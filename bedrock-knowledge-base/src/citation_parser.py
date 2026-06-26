import urllib.parse
from typing import Dict, Any, List, Optional

def parse_citations(retrieval_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parses Amazon Bedrock Knowledge Base retrieval results into a clean list of citation dictionaries.

    Args:
        retrieval_results (list): The list of results returned from the retrieve API ('retrievalResults').

    Returns:
        list: A list of dicts, each containing:
            - 'source_file' (str): The unquoted filename of the source document.
            - 'page_number' (int or None): The 1-based page number, cast to an integer.
            - 'text' (str): The raw text content of the chunk.
            - 'score' (float): The retrieval confidence score.
            - 'uri' (str): The raw S3 URI.
    """
    citations = []
    for result in retrieval_results:
        # Extract location URI
        uri = result.get('location', {}).get('s3Location', {}).get('uri', '')
        source_file = 'Unknown Source'
        if uri:
            # Get the last segment of the URI path and URL-decode it
            filename_segment = uri.split('/')[-1]
            source_file = urllib.parse.unquote(filename_segment)
            
        # Extract page number from metadata dictionary
        metadata = result.get('metadata', {})
        page_number = metadata.get('x-amz-bedrock-kb-document-page-number')
        
        parsed_page = None
        if page_number is not None:
            try:
                parsed_page = int(float(page_number))
            except (ValueError, TypeError):
                # Fallback to whatever value it is if casting fails
                parsed_page = page_number

        text = result.get('content', {}).get('text', '')
        score = result.get('score', 0.0)
        
        citations.append({
            'source_file': source_file,
            'page_number': parsed_page,
            'text': text,
            'score': score,
            'uri': uri
        })
    return citations

def deduplicate_citation_references(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates citations to extract a clean list of unique document sources and pages referenced,
    preserving the order of appearance.

    Args:
        citations (list): The parsed list of citations from parse_citations.

    Returns:
        list: A deduplicated list of dicts containing 'source_file' and 'page_number'.
    """
    seen = set()
    deduped = []
    for cit in citations:
        ref_key = (cit['source_file'], cit['page_number'])
        if ref_key not in seen:
            seen.add(ref_key)
            deduped.append({
                'source_file': cit['source_file'],
                'page_number': cit['page_number']
            })
    return deduped
