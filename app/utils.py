from SPARQLWrapper import SPARQLWrapper, JSON, POST, DIGEST
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def execute_select(query):
    """
    Execute a SPARQL SELECT query against the Virtuoso endpoint.
    """
    sparql = SPARQLWrapper(settings.VIRTUOSO_SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    sparql.setMethod('GET')
    sparql.setHTTPAuth(DIGEST)  # Use DIGEST authentication for /sparql-auth
    sparql.setCredentials('dba', 'dba')  # Matches DBA_PASSWORD in docker-compose.yml
    try:
        results = sparql.query().convert()
        logger.debug(f"SELECT query executed: {query}")
        return results
    except Exception as e:
        logger.error(f"Error executing SELECT query: {str(e)}")
        raise

def execute_update(query):
    """
    Execute a SPARQL UPDATE (INSERT/DELETE) query against the Virtuoso endpoint.
    """
    sparql = SPARQLWrapper(settings.VIRTUOSO_SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setMethod(POST)
    sparql.setHTTPAuth(DIGEST)
    sparql.setCredentials('dba', 'dba')  # Matches DBA_PASSWORD in docker-compose.yml
    try:
        response = sparql.query()
        logger.debug(f"UPDATE query response: {response.response.read()}")
        logger.debug(f"UPDATE query executed: {query}")
    except Exception as e:
        logger.error(f"Error executing UPDATE query: {str(e)}")
        raise