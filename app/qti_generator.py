import xml.etree.ElementTree as ET
from django.core.exceptions import ObjectDoesNotExist
import random
from app.models import Test

def generate_qti(test_id):
    try:
        test = Test.objects.get(id=test_id)
        test_title = test.title
        questions = test.questions.all()

        qti_root = ET.Element("qti-assessment", xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0",
                              xsi_schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0 "
                                                 "https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0p1_v1p0.xsd",
                              xml_lang="en-US")
        
        for question in questions:
            question_text = question.text
            correct_answer = question.correct_answer
            other_answers = question.other_answers
            all_answers = [correct_answer] + other_answers

            shuffled_answers = all_answers[:]
            random.shuffle(shuffled_answers)

            assessment_item = ET.SubElement(qti_root, "qti-assessment-item", 
                                            identifier=f"item_{question.id}", 
                                            title=question_text, 
                                            adaptive="false", 
                                            time_dependent="false")

            response_declaration = ET.SubElement(assessment_item, "qti-response-declaration", 
                                                 identifier="RESPONSE", 
                                                 cardinality="single", 
                                                 base_type="identifier")
            correct_response = ET.SubElement(response_declaration, "qti-correct-response")
            correct_answer_index = shuffled_answers.index(correct_answer)
            ET.SubElement(correct_response, "qti-value").text = f"answer_{correct_answer_index}"

            item_body = ET.SubElement(assessment_item, "qti-item-body")
            choice_interaction = ET.SubElement(item_body, "qti-choice-interaction", 
                                               response_identifier="RESPONSE", 
                                               shuffle="false", 
                                               max_choices="1")
            prompt = ET.SubElement(choice_interaction, "qti-prompt")
            prompt.text = question_text

            for idx, answer in enumerate(shuffled_answers):
                simple_choice = ET.SubElement(choice_interaction, "qti-simple-choice", 
                                              identifier=f"answer_{idx}")  
                simple_choice.text = answer

            response_processing = ET.SubElement(assessment_item, "qti-response-processing")
            set_outcome_value = ET.SubElement(response_processing, "qti-set-outcome-value", 
                                              identifier="FEEDBACK")
            ET.SubElement(set_outcome_value, "qti-base-value", base_type="identifier").text = "NOHINT"
            
            response_condition = ET.SubElement(response_processing, "qti-response-condition")
            response_if = ET.SubElement(response_condition, "qti-response-if")
            match = ET.SubElement(response_if, "qti-match")
            ET.SubElement(match, "qti-variable", identifier="RESPONSE")
            ET.SubElement(match, "qti-correct", identifier="RESPONSE")
            set_outcome_value_score = ET.SubElement(response_if, "qti-set-outcome-value", 
                                                     identifier="SCORE")
            ET.SubElement(set_outcome_value_score, "qti-base-value", base_type="float").text = "1"
            
            response_else = ET.SubElement(response_condition, "qti-response-else")
            set_outcome_value_score_else = ET.SubElement(response_else, "qti-set-outcome-value", 
                                                         identifier="SCORE")
            ET.SubElement(set_outcome_value_score_else, "qti-base-value", base_type="float").text = "0"

        tree = ET.ElementTree(qti_root)
        return tree

    except ObjectDoesNotExist:
        print(f"Test with ID {test_id} not found!")
