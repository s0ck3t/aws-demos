import os
import boto3
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.citation_parser import parse_citations, deduplicate_citation_references

DEFAULT_MODEL_ID = 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
DEFAULT_REGION = 'eu-west-2'
FALLBACK_MESSAGE = "I cannot find this information in the policy documents."

def resolve_kb_id() -> str:
    """
    Attempts to resolve the Knowledge Base ID from environment variables
    or from the local .ingestion_job_info file.
    """
    # 1. Check environment variable
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
    if kb_id:
        return kb_id

    # 2. Check local bootstrap file
    # Searches in current dir, parent dir, or project root
    for parent in [Path.cwd(), Path(__file__).resolve().parent.parent]:
        info_path = parent / ".ingestion_job_info"
        if info_path.exists():
            try:
                with open(info_path, "r") as f:
                    parts = f.read().strip().split(",")
                    if len(parts) >= 1 and parts[0]:
                        return parts[0]
            except Exception:
                pass

    raise ValueError(
        "Knowledge Base ID could not be resolved. Please set the KNOWLEDGE_BASE_ID "
        "environment variable or ensure .ingestion_job_info is present in the project root."
    )

def query_policy_oracle(
    query: str,
    kb_id: Optional[str] = None,
    model_id: str = DEFAULT_MODEL_ID,
    region_name: str = DEFAULT_REGION,
    score_threshold: float = 0.60
) -> Dict[str, Any]:
    """
    Orchestrates the retrieval of policy context and the generation of a grounded answer.

    Args:
        query (str): The user's policy-related question.
        kb_id (str, optional): The Bedrock Knowledge Base ID. If omitted, it resolves automatically.
        model_id (str): The foundation model or inference profile ID to use for generation.
        region_name (str): The AWS region to target.
        score_threshold (float): The minimum relevance score required. Below this, LLM is bypassed
                                 and the default fallback is returned.

    Returns:
        dict: A dictionary containing:
            - 'answer' (str): The generated response or fallback message.
            - 'citations' (list): The list of parsed retrieval result dictionaries.
            - 'references' (list): Deduplicated list of source files and page numbers.
    """
    if not kb_id:
        kb_id = resolve_kb_id()

    agent_client = boto3.client('bedrock-agent-runtime', region_name=region_name)
    runtime_client = boto3.client('bedrock-runtime', region_name=region_name)

    # 1. Retrieve relevant passages from the Knowledge Base
    try:
        retrieve_response = agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': query}
        )
    except Exception as e:
        # If retrieval fails, wrap and propagate or handle gracefully
        raise RuntimeError(f"Failed to query Bedrock Knowledge Base: {e}")

    results = retrieve_response.get('retrievalResults', [])
    citations = parse_citations(results)

    # 2. Confidence Boundary Check
    # If no documents are retrieved or all retrieved documents are below the score threshold
    if not citations or max(c['score'] for c in citations) < score_threshold:
        return {
            'answer': FALLBACK_MESSAGE,
            'citations': [],
            'references': []
        }

    # 3. Format the context for the generator model
    context_blocks = []
    for i, cit in enumerate(citations):
        context_blocks.append(
            f"Reference #{i+1}\n"
            f"Source Document: {cit['source_file']}\n"
            f"Source Page: {cit['page_number']}\n"
            f"Relevance Score: {cit['score']:.4f}\n"
            f"Content:\n{cit['text']}\n"
            "----------------------------------------"
        )
    context_str = "\n".join(context_blocks)

    # 4. Construct System Prompt & User Message for Claude 4.5 Sonnet
    system_prompt = (
        "You are 'The Brentwood Policy Oracle', an expert public housing policy assistant for Brentwood Borough Council.\n"
        "Your task is to answer the user's policy query using ONLY the provided references from the policy documents.\n"
        "Ground your answers strictly in the text. Do not make up facts, guess, or extrapolate beyond what is written.\n"
        "Be extremely concise, direct, and factual. Do not add conversational filler, introductory remarks, or summary. Only output sentences that are directly supported by the references.\n"
        "If the provided context does not contain enough information to answer the question, or if the context is "
        "not relevant to the question, you must respond with exactly: \"I cannot find this information in the policy documents.\"\n"
        "Do not explain why you cannot find it, and do not add any other notes or warnings. Just output that exact sentence."
    )

    user_prompt = (
        f"Retrieved Policy References:\n{context_str}\n\n"
        f"User Query: {query}\n"
        f"Answer:"
    )

    # 5. Invoke Claude 4.5 Sonnet using Converse API
    try:
        generation_response = runtime_client.converse(
            modelId=model_id,
            system=[{'text': system_prompt}],
            messages=[
                {
                    'role': 'user',
                    'content': [{'text': user_prompt}]
                }
            ]
        )
        answer = generation_response['output']['message']['content'][0]['text'].strip()
    except Exception as e:
        raise RuntimeError(f"Failed to generate answer using Bedrock Runtime: {e}")

    # 6. Deduplicate page references for clean user reporting
    references = deduplicate_citation_references(citations)

    return {
        'answer': answer,
        'citations': citations,
        'references': references
    }
