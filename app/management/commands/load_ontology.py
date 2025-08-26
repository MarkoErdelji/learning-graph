from django.conf import settings
from django.core.management.base import BaseCommand
from rdflib import Graph
from app.settings import SOTIS_GRAPH
import os

from app.utils import execute_update

class Command(BaseCommand):
    help = 'Load ontology from lom.owl into Virtuoso'

    def handle(self, *args, **kwargs):
        # Define the path to the OWL file relative to the project root
        owl_file_path = os.path.join(settings.BASE_DIR, 'virtuoso/data/lom.owl')

        # Check if the file exists
        if not os.path.exists(owl_file_path):
            self.stdout.write(self.style.ERROR(f'OWL file not found at: {owl_file_path}'))
            return

        # Parse the OWL file
        try:
            g = Graph()
            g.parse(owl_file_path, format='xml')  # Use 'xml' for RDF/XML; change to 'turtle' if needed
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to parse OWL file: {str(e)}'))
            return

        # Serialize triples into SPARQL INSERT DATA format
        triples = []
        for subj, pred, obj in g:
            # Convert RDF terms to SPARQL-compatible strings
            def format_term(term):
                if term.startswith('http://') or term.startswith('https://'):
                    return f'<{term}>'
                elif term.startswith('_:'):
                    return term  # Blank node
                else:
                    return f'"{term}"'  # Literal

            subj_str = format_term(str(subj))
            pred_str = format_term(str(pred))
            obj_str = format_term(str(obj))
            triples.append(f'{subj_str} {pred_str} {obj_str} .')

        if not triples:
            self.stdout.write(self.style.WARNING('No triples found in the OWL file'))
            return

        # Batch triples to avoid large query issues
        batch_size = 1000
        for i in range(0, len(triples), batch_size):
            batch = triples[i:i + batch_size]
            query = f"""
            PREFIX lom: <{settings.LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{settings.SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    {' '.join(batch)}
                }}
            }}
            """
            try:
                execute_update(query)
                self.stdout.write(self.style.SUCCESS(f'Inserted batch {i // batch_size + 1} of triples'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to insert batch {i // batch_size + 1}: {str(e)}'))
                return

        self.stdout.write(self.style.SUCCESS('Ontology loaded successfully'))