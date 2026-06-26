import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.citation_parser import parse_citations, deduplicate_citation_references
from src.orchestrator import query_policy_oracle, resolve_kb_id, FALLBACK_MESSAGE

# Sample mock retrieval results from Bedrock retrieve API
MOCK_RETRIEVE_RESULTS = [
    {
        'content': {'text': 'This is policy section one.'},
        'location': {
            's3Location': {'uri': 's3://my-bucket/Pets%20Policy%202025%20-%202028.pdf'},
            'type': 'S3'
        },
        'metadata': {
            'x-amz-bedrock-kb-source-file-modality': 'TEXT',
            'x-amz-bedrock-kb-document-page-number': 3.0,
            'x-amz-bedrock-kb-data-source-id': 'MOCK_DS'
        },
        'score': 0.85
    },
    {
        'content': {'text': 'This is policy section two.'},
        'location': {
            's3Location': {'uri': 's3://my-bucket/Pets%20Policy%202025%20-%202028.pdf'},
            'type': 'S3'
        },
        'metadata': {
            'x-amz-bedrock-kb-source-file-modality': 'TEXT',
            'x-amz-bedrock-kb-document-page-number': 3.0,
            'x-amz-bedrock-kb-data-source-id': 'MOCK_DS'
        },
        'score': 0.75
    },
    {
        'content': {'text': 'This is decant section.'},
        'location': {
            's3Location': {'uri': 's3://my-bucket/Decant%20Policy.pdf'},
            'type': 'S3'
        },
        'metadata': {
            'x-amz-bedrock-kb-source-file-modality': 'TEXT',
            'x-amz-bedrock-kb-document-page-number': 1.0,
            'x-amz-bedrock-kb-data-source-id': 'MOCK_DS'
        },
        'score': 0.65
    }
]

def test_parse_citations():
    """Assert that parse_citations correctly parses Bedrock retrieve JSON response."""
    citations = parse_citations(MOCK_RETRIEVE_RESULTS)
    
    assert len(citations) == 3
    
    # Assert unquoting of filename works
    assert citations[0]['source_file'] == 'Pets Policy 2025 - 2028.pdf'
    assert citations[2]['source_file'] == 'Decant Policy.pdf'
    
    # Assert float to int page number conversion
    assert citations[0]['page_number'] == 3
    assert citations[2]['page_number'] == 1
    
    # Assert score and text mapping
    assert citations[0]['score'] == 0.85
    assert citations[0]['text'] == 'This is policy section one.'

def test_deduplicate_citation_references():
    """Assert that deduplicate_citation_references returns unique (file, page) references in order."""
    citations = parse_citations(MOCK_RETRIEVE_RESULTS)
    references = deduplicate_citation_references(citations)
    
    assert len(references) == 2
    assert references[0] == {'source_file': 'Pets Policy 2025 - 2028.pdf', 'page_number': 3}
    assert references[1] == {'source_file': 'Decant Policy.pdf', 'page_number': 1}

def test_resolve_kb_id_from_env():
    """Assert resolve_kb_id prioritizes environment variables."""
    with patch.dict(os.environ, {"KNOWLEDGE_BASE_ID": "ENV_KB_ID"}):
        kb_id = resolve_kb_id()
        assert kb_id == "ENV_KB_ID"

def test_resolve_kb_id_from_file(tmp_path):
    """Assert resolve_kb_id reads from local file when env is absent."""
    mock_file = tmp_path / ".ingestion_job_info"
    mock_file.write_text("FILE_KB_ID,DS_ID,JOB_ID")
    
    with patch.dict(os.environ, {}, clear=True):
        with patch('pathlib.Path.exists', return_value=True):
            # Patch open to read from our mock file
            with patch('builtins.open', mock_open(read_data="FILE_KB_ID,DS_ID,JOB_ID")):
                kb_id = resolve_kb_id()
                assert kb_id == "FILE_KB_ID"

def test_resolve_kb_id_failure():
    """Assert resolve_kb_id raises ValueError when KB ID cannot be resolved."""
    with patch.dict(os.environ, {}, clear=True):
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(ValueError, match="Knowledge Base ID could not be resolved"):
                resolve_kb_id()

@patch('boto3.client')
def test_query_policy_oracle_low_score(mock_boto_client):
    """Assert that queries below score threshold bypass LLM and return fallback message."""
    mock_agent_runtime = MagicMock()
    mock_runtime = MagicMock()
    
    # Configure retrieve to return low scores
    low_score_results = [
        {
            'content': {'text': 'Unrelated content.'},
            'location': {'s3Location': {'uri': 's3://bucket/Doc.pdf'}, 'type': 'S3'},
            'metadata': {'x-amz-bedrock-kb-document-page-number': 1.0},
            'score': 0.50
        }
    ]
    mock_agent_runtime.retrieve.return_value = {'retrievalResults': low_score_results}
    
    # Set up client factory mock
    def client_side_effect(service_name, **kwargs):
        if service_name == 'bedrock-agent-runtime':
            return mock_agent_runtime
        elif service_name == 'bedrock-runtime':
            return mock_runtime
        return MagicMock()
        
    mock_boto_client.side_effect = client_side_effect
    
    result = query_policy_oracle("What is the capital of France?", kb_id="TEST_KB", score_threshold=0.60)
    
    assert result['answer'] == FALLBACK_MESSAGE
    assert result['citations'] == []
    assert result['references'] == []
    
    # Assert retrieve was called, but converse was NOT called (bypassed)
    mock_agent_runtime.retrieve.assert_called_once()
    mock_runtime.converse.assert_not_called()

@patch('boto3.client')
def test_query_policy_oracle_empty_results(mock_boto_client):
    """Assert that empty retrieval results bypass LLM and return fallback message."""
    mock_agent_runtime = MagicMock()
    mock_runtime = MagicMock()
    
    mock_agent_runtime.retrieve.return_value = {'retrievalResults': []}
    
    def client_side_effect(service_name, **kwargs):
        if service_name == 'bedrock-agent-runtime':
            return mock_agent_runtime
        elif service_name == 'bedrock-runtime':
            return mock_runtime
        return MagicMock()
        
    mock_boto_client.side_effect = client_side_effect
    
    result = query_policy_oracle("Any query?", kb_id="TEST_KB")
    
    assert result['answer'] == FALLBACK_MESSAGE
    assert result['citations'] == []
    assert result['references'] == []
    
    mock_agent_runtime.retrieve.assert_called_once()
    mock_runtime.converse.assert_not_called()

@patch('boto3.client')
def test_query_policy_oracle_valid(mock_boto_client):
    """Assert that a valid query invokes LLM and returns answer and citations."""
    mock_agent_runtime = MagicMock()
    mock_runtime = MagicMock()
    
    # Mock retrieve
    mock_agent_runtime.retrieve.return_value = {'retrievalResults': MOCK_RETRIEVE_RESULTS}
    
    # Mock converse API return value
    mock_converse_response = {
        'output': {
            'message': {
                'content': [{'text': 'Based on pets policy page 3, pets are allowed.'}]
            }
        }
    }
    mock_runtime.converse.return_value = mock_converse_response
    
    def client_side_effect(service_name, **kwargs):
        if service_name == 'bedrock-agent-runtime':
            return mock_agent_runtime
        elif service_name == 'bedrock-runtime':
            return mock_runtime
        return MagicMock()
        
    mock_boto_client.side_effect = client_side_effect
    
    result = query_policy_oracle("What is the policy on pets?", kb_id="TEST_KB", score_threshold=0.60)
    
    assert result['answer'] == 'Based on pets policy page 3, pets are allowed.'
    assert len(result['citations']) == 3
    assert len(result['references']) == 2
    
    # Assert both APIs were called
    mock_agent_runtime.retrieve.assert_called_once()
    mock_runtime.converse.assert_called_once()
