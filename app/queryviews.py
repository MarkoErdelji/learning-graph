from rest_framework.views import APIView
from rest_framework.response import Response
from app.permissions import IsTeacher
from app.utils import execute_select


# ========================
# STUDENT ANALYTICS VIEWS
# ========================

class StudentOverallAverageView(APIView):
    """
    Returns the student's overall test statistics:
    - Number of tests taken
    - Average score
    - Best score
    - Worst score
    """
    def get(self, request):
        user_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT 
          (COUNT(?attempt) AS ?testsTaken)
          (AVG(?score) AS ?avgScore)
          (MAX(?score) AS ?bestScore)
          (MIN(?score) AS ?worstScore)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt a sotis:TestAttempt ;
                     lom:contributor {user_uri} ;
                     sotis:score ?score .
          }}
        }}
        """

        results = execute_select(query)
        b = results["results"]["bindings"][0] if results["results"]["bindings"] else {}

        data = {
            "tests_taken": int(b.get("testsTaken", {}).get("value", 0)),
            "average_score": round(float(b.get("avgScore", {}).get("value", 0) or 0), 1),
            "best_score": round(float(b.get("bestScore", {}).get("value", 0) or 0), 1),
            "worst_score": round(float(b.get("worstScore", {}).get("value", 0) or 0), 1)
        }
        return Response(data)


class StudentRecentTestsView(APIView):
    """
    Returns the student's 6 most recent tests with:
    - Test title
    - Score
    - Date
    - Trend indicator compared to previous test
    """
    def get(self, request):
        user_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?testTitle ?score ?dateRaw
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt a sotis:TestAttempt ;
                     lom:contributor {user_uri} ;
                     lom:partOf ?test ;
                     sotis:score ?score ;
                     lom:date ?dateRaw .
            ?test lom:title ?testTitle .
          }}
        }}
        ORDER BY DESC(xsd:dateTime(?dateRaw))
        LIMIT 6
        """

        results = execute_select(query)
        data = []
        prev_score = None
        for b in results["results"]["bindings"]:
            score = round(float(b["score"]["value"]), 1)
            date_str = b["dateRaw"]["value"]
            date_display = date_str[:10] if 'T' in date_str else date_str[:10]
            trend = "↑" if prev_score is not None and score > prev_score + 3 else \
                    "↓" if prev_score is not None and score < prev_score - 3 else "→"
            data.append({
                "test": b["testTitle"]["value"],
                "score": score,
                "date": date_display,
                "trend": trend
            })
            prev_score = score
        return Response(data[::-1])  # Return oldest first


class StudentTopicMasteryView(APIView):
    """
    Returns the student's performance per topic (node):
    - Topic name
    - Number of questions answered
    - Number of correct answers
    - Performance percentage
    Ordered by best performance.
    """
    def get(self, request):
        user_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?topic ?questions ?correct ?performance
        WHERE {{
          {{
            SELECT ?node
                   (COUNT(*) AS ?questions)
                   (SUM(IF(?isCorrect = "true"^^xsd:boolean, 1, 0)) AS ?correct)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?attempt lom:contributor {user_uri} ;
                         sotis:hasAnswer ?ans .
                ?ans sotis:question ?q ;
                     sotis:isCorrect ?isCorrect .
                ?q lom:partOf ?node .
              }}
            }}
            GROUP BY ?node
            HAVING (COUNT(*) > 0)
          }}
          ?node lom:title ?topic .
          BIND(IF(?questions > 0, ?correct * 100.0 / ?questions, 0) AS ?performance)
        }}
        ORDER BY DESC(?performance)
        """

        results = execute_select(query)
        data = [
            {
                "topic": b["topic"]["value"],
                "questions_answered": int(b["questions"]["value"]),
                "correct_answers": int(b["correct"]["value"]),
                "performance_percent": round(float(b["performance"]["value"]), 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class StudentFrequentlyWrongView(APIView):
    """
    Returns the 5 topics where the student has the highest error rate
    (only topics with at least 4 questions answered).
    """
    def get(self, request):
        user_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?topic ?total ?wrong ?errorRate
        WHERE {{
          {{
            SELECT ?node
                   (COUNT(*) AS ?total)
                   (SUM(IF(?isCorrect = "false"^^xsd:boolean, 1, 0)) AS ?wrong)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?attempt lom:contributor {user_uri} ;
                         sotis:hasAnswer ?ans .
                ?ans sotis:question ?q ;
                     sotis:isCorrect ?isCorrect .
                ?q lom:partOf ?node .
              }}
            }}
            GROUP BY ?node
            HAVING (COUNT(*) >= 4)
          }}
          ?node lom:title ?topic .
          BIND(?wrong * 100.0 / ?total AS ?errorRate)
        }}
        ORDER BY DESC(?errorRate)
        LIMIT 5
        """

        results = execute_select(query)
        data = [
            {
                "topic": b["topic"]["value"],
                "total_questions": int(b["total"]["value"]),
                "wrong_answers": int(b["wrong"]["value"]),
                "error_rate_percent": round(float(b["errorRate"]["value"]), 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class StudentRankingView(APIView):
    """
    Returns the current student's class rank based on average score across all students.
    Also includes top 5 leaderboard.
    """
    def get(self, request):
        query = """
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?student ?studentName (AVG(?score) AS ?avgScore)
        WHERE {
          GRAPH <http://example.com/sotis/graph> {
            ?attempt a sotis:TestAttempt ;
                     lom:contributor ?student ;
                     sotis:score ?score .
            ?student lom:title ?studentName .
          }
        }
        GROUP BY ?student ?studentName
        ORDER BY DESC(?avgScore)
        """

        results = execute_select(query)
        ranked = []
        my_rank = None
        my_score = None
        current_user_uri = f"http://example.com/sotis#user/{request.user.username}"

        for i, b in enumerate(results["results"]["bindings"], 1):
            name = b["studentName"]["value"]
            score = round(float(b["avgScore"]["value"]), 1)
            uri = b["student"]["value"]

            ranked.append({"rank": i, "name": name, "score": score})

            if uri == current_user_uri:
                my_rank = i
                my_score = score

        return Response({
            "my_rank": my_rank or "N/A",
            "my_score": my_score or 0.0,
            "total_students": len(ranked),
            "top_5": ranked[:5]
        })


class StudentRecommendationsView(APIView):
    """
    Returns up to 6 topics where the student's mastery is below the given threshold (default 70%).
    Used for personalized review recommendations.
    """
    def get(self, request):
        threshold_percent = float(request.query_params.get('threshold', 70))
        user_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?topic ?mastery ?questions
        WHERE {{
          {{
            SELECT ?node (AVG(IF(?isCorrect = "true"^^xsd:boolean, 1.0, 0.0)) AS ?mastery) (COUNT(*) AS ?questions)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?attempt lom:contributor {user_uri} ;
                         sotis:hasAnswer ?ans .
                ?ans sotis:question ?q ;
                     sotis:isCorrect ?isCorrect .
                ?q lom:partOf ?node .
              }}
            }}
            GROUP BY ?node
            HAVING (AVG(IF(?isCorrect = "true"^^xsd:boolean, 1.0, 0.0)) * 100 < {threshold_percent})
          }}
          ?node lom:title ?topic .
        }}
        ORDER BY ?mastery
        LIMIT 6
        """

        results = execute_select(query)
        data = [
            {
                "topic": b["topic"]["value"],
                "mastery_percent": round(float(b["mastery"]["value"]) * 100, 1),
                "questions": int(b["questions"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


# ========================
# TEACHER ANALYTICS VIEWS
# ========================

class ClassAveragePerTestView(APIView):
    """
    Returns average score and number of participants for each of the teacher's tests.
    """
    permission_classes = [IsTeacher]
    
    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?testTitle ?participants ?averageScore
        WHERE {{
          {{
            SELECT ?test
                   (COUNT(*) AS ?participants)
                   (AVG(?score) AS ?averageScore)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?test lom:contributor {teacher_uri} .
                ?attempt a sotis:TestAttempt ;
                         lom:partOf ?test ;
                         sotis:score ?score .
              }}
            }}
            GROUP BY ?test
          }}
          ?test lom:title ?testTitle .
        }}
        ORDER BY DESC(?averageScore)
        """

        results = execute_select(query)
        data = [
            {
                "test": b["testTitle"]["value"],
                "participants": int(b["participants"]["value"]),
                "average_score": round(float(b["averageScore"]["value"]), 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class ClassHardestQuestionsView(APIView):
    """
    Returns the hardest questions in the teacher's tests based on failure rate.
    Uses full question text from lom:description when available, falls back to lom:title.
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?questionText ?failureRate ?attempted
        WHERE {{
          {{
            SELECT ?q
                   ((1.0 - AVG(IF(?isCorrect = "true"^^xsd:boolean, 1.0, 0.0))) * 100 AS ?failureRate)
                   (COUNT(*) AS ?attempted)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?test lom:contributor {teacher_uri} .
                ?attempt a sotis:TestAttempt ;
                         lom:partOf ?test ;
                         sotis:hasAnswer ?ans .
                ?ans sotis:question ?q ;
                     sotis:isCorrect ?isCorrect .
              }}
            }}
            GROUP BY ?q
            HAVING (COUNT(*) >= 3)
          }}

          GRAPH <http://example.com/sotis/graph> {{
            OPTIONAL {{ ?q lom:description ?fullText }}
            OPTIONAL {{ ?q lom:title ?shortText }}
            BIND(COALESCE(?fullText, ?shortText, "Unknown question") AS ?questionText)
          }}
        }}
        ORDER BY DESC(?failureRate) DESC(?attempted)
        LIMIT 15
        """

        results = execute_select(query)
        data = [
            {
                "question": b["questionText"]["value"][:70] + "..." if len(b["questionText"]["value"]) > 70 else b["questionText"]["value"],
                "failure_rate_percent": round(float(b["failureRate"]["value"]), 1),
                "attempted": int(b["attempted"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class StudentsNeedingHelpView(APIView):
    """
    Returns students with average score below threshold (default 60%) on the teacher's tests.
    """
    permission_classes = [IsTeacher]
    
    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"
        threshold_percent = float(request.query_params.get('threshold', 60))

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?studentName ?avgScore ?testsTaken
        WHERE {{
          {{
            SELECT ?student (AVG(?score) AS ?avgScore) (COUNT(?attempt) AS ?testsTaken)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?test lom:contributor {teacher_uri} .
                ?attempt a sotis:TestAttempt ;
                         lom:contributor ?student ;
                         lom:partOf ?test ;
                         sotis:score ?score .
              }}
            }}
            GROUP BY ?student
            HAVING (AVG(?score) < {threshold_percent})
          }}
          GRAPH <http://example.com/sotis/graph> {{
            ?student lom:title ?studentName .
          }}
        }}
        ORDER BY ?avgScore
        LIMIT 10
        """

        results = execute_select(query)
        data = [
            {
                "name": b["studentName"]["value"],
                "average_score": round(float(b["avgScore"]["value"]), 1),
                "tests_taken": int(b["testsTaken"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class ClassTopicMasteryView(APIView):
    """
    Returns class-wide mastery per topic on the teacher's tests.
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?topic ?questionsAnswered ?classMastery
        WHERE {{
          {{
            SELECT ?node
                   (COUNT(*) AS ?questionsAnswered)
                   (AVG(IF(?isCorrect = "true"^^xsd:boolean, 1.0, 0.0)) AS ?classMastery)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?test lom:contributor {teacher_uri} .
                ?attempt a sotis:TestAttempt ;
                         lom:partOf ?test ;
                         sotis:hasAnswer ?ans .
                ?ans sotis:question ?q ;
                     sotis:isCorrect ?isCorrect .
                ?q lom:partOf ?node .
              }}
            }}
            GROUP BY ?node
          }}
          ?node lom:title ?topic .
        }}
        ORDER BY DESC(?classMastery)
        """

        results = execute_select(query)
        data = [
            {
                "topic": b["topic"]["value"],
                "questions_answered": int(b["questionsAnswered"]["value"]),
                "class_mastery_percent": round(float(b["classMastery"]["value"]) * 100, 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class TestParticipationView(APIView):
    """
    Returns number of unique participants per test for the teacher.
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>

        SELECT ?testTitle ?participants
        WHERE {{
          {{
            SELECT ?test (COUNT(DISTINCT ?student) AS ?participants)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?test lom:contributor {teacher_uri} .
                ?attempt a sotis:TestAttempt ;
                         lom:contributor ?student ;
                         lom:partOf ?test .
              }}
            }}
            GROUP BY ?test
          }}
          ?test lom:title ?testTitle .
        }}
        ORDER BY DESC(?participants)
        """

        results = execute_select(query)
        data = [
            {
                "test": b["testTitle"]["value"],
                "participants": int(b["participants"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class MostImprovedStudentsView(APIView):
    """
    Returns the top 10 most improved students on the teacher's tests
    (students with at least 2 attempts and positive improvement).
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?studentName ?firstScore ?lastScore (?lastScore - ?firstScore AS ?improvement)
        WHERE {{
            # Subquery: Identify students with ≥2 attempts and their first/last dates
            {{
                SELECT ?student (MIN(xsd:dateTime(?dateRaw)) AS ?firstDate) (MAX(xsd:dateTime(?dateRaw)) AS ?lastDate)
                WHERE {{
                    GRAPH <http://example.com/sotis/graph> {{
                        ?test lom:contributor {teacher_uri} .
                        ?attempt a sotis:TestAttempt ;
                                 lom:contributor ?student ;
                                 lom:partOf ?test ;
                                 lom:date ?dateRaw .
                    }}
                }}
                GROUP BY ?student
                HAVING (COUNT(?attempt) >= 2)
            }}

            # First attempt score (earliest date)
            GRAPH <http://example.com/sotis/graph> {{
                ?firstAttempt a sotis:TestAttempt ;
                              lom:contributor ?student ;
                              sotis:score ?firstScore ;
                              lom:date ?firstDateRaw .
            }}
            FILTER(xsd:dateTime(?firstDateRaw) = ?firstDate)

            # Last attempt score (latest date)
            GRAPH <http://example.com/sotis/graph> {{
                ?lastAttempt a sotis:TestAttempt ;
                             lom:contributor ?student ;
                             sotis:score ?lastScore ;
                             lom:date ?lastDateRaw .
            }}
            FILTER(xsd:dateTime(?lastDateRaw) = ?lastDate)

            # Student name
            GRAPH <http://example.com/sotis/graph> {{
                ?student lom:title ?studentName .
            }}

            FILTER(?lastScore > ?firstScore)
        }}
        ORDER BY DESC(?improvement)
        LIMIT 10
        """

        results = execute_select(query)

        data = [
            {
                "student": b["studentName"]["value"],
                "first_score": round(float(b["firstScore"]["value"]), 1),
                "latest_score": round(float(b["lastScore"]["value"]), 1),
                "improvement": round(float(b["improvement"]["value"]), 1)
            }
            for b in results["results"]["bindings"]
        ]

        return Response(data)


class ClassPrerequisiteViolationsView(APIView):
    """
    Returns class-level prerequisite violations:
    Cases where many students master a prerequisite topic but fail the advanced topic that depends on it.
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"
        min_students = int(request.query_params.get('min_students', 3))

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?prereqTopic ?advancedTopic ?prereqSuccess ?advancedFailure ?affected
        WHERE {{
          {{
            SELECT ?prereq ?advanced
                   (AVG(?prereqCorrect) AS ?prereqSuccess)
                   (AVG(?advancedIncorrect) AS ?advancedFailure)
                   (COUNT(DISTINCT ?student) AS ?affected)
            WHERE {{
              GRAPH <http://example.com/sotis/graph> {{
                ?advanced lom:requires ?prereq .
              }}

              OPTIONAL {{
                GRAPH <http://example.com/sotis/graph> {{
                  ?test lom:contributor {teacher_uri} .
                  ?attempt a sotis:TestAttempt ;
                           lom:contributor ?student ;
                           lom:partOf ?test ;
                           sotis:hasAnswer ?ans .
                  ?ans sotis:question ?q ;
                       sotis:isCorrect ?correctRaw .
                  ?q lom:partOf ?prereq .
                  BIND(IF(?correctRaw = "true"^^xsd:boolean, 1.0, 0.0) AS ?prereqCorrect)
                }}
              }}

              OPTIONAL {{
                GRAPH <http://example.com/sotis/graph> {{
                  ?test2 lom:contributor {teacher_uri} .
                  ?attempt2 a sotis:TestAttempt ;
                            lom:contributor ?student ;
                            lom:partOf ?test2 ;
                            sotis:hasAnswer ?ans2 .
                  ?ans2 sotis:question ?q2 ;
                        sotis:isCorrect ?correctRaw2 .
                  ?q2 lom:partOf ?advanced .
                  BIND(IF(?correctRaw2 = "false"^^xsd:boolean, 1.0, 0.0) AS ?advancedIncorrect)
                }}
              }}

              FILTER(BOUND(?prereqCorrect) && BOUND(?advancedIncorrect))
            }}
            GROUP BY ?prereq ?advanced
            HAVING (COUNT(DISTINCT ?student) >= {min_students})
          }}

          GRAPH <http://example.com/sotis/graph> {{
            ?prereq lom:title ?prereqTopic .
            ?advanced lom:title ?advancedTopic .
          }}

          FILTER(?prereqSuccess > 0.7 && ?advancedFailure > 0.4)
        }}
        ORDER BY DESC(?affected) DESC(?advancedFailure)
        LIMIT 10
        """

        results = execute_select(query)
        data = [
            {
                "prerequisite": b["prereqTopic"]["value"],
                "advanced": b["advancedTopic"]["value"],
                "prereq_success_percent": round(float(b["prereqSuccess"]["value"]) * 100, 1),
                "advanced_failure_percent": round(float(b["advancedFailure"]["value"]) * 100, 1),
                "students_affected": int(b["affected"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)
    