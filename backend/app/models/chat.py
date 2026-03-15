from typing import List
from abc import ABC, abstractmethod
from transformers import AutoTokenizer, AutoModelForCausalLM
from qdrant_client import QdrantClient
from app.__init__ import (
    CHAT_MODEL, 
    CHAT_MODEL_CONTEXT_LENGTH,
    MODEL_PROVIDER,
    CHAT_MODEL_NAME
)
from app.models.chat_history import get_chat_messages
import torch


class BaseChatModel(ABC):
    """Abstract base class for chat models."""
    
    @abstractmethod
    def get_response(self, prompt: str, max_new_tokens: int = 512) -> str:
        """Generate response from the model."""
        pass
    
    @abstractmethod
    def get_chat_response(self, messages: List[dict], max_new_tokens: int = 512) -> str:
        """Generate response from chat messages format."""
        pass


class LocalChatModel(BaseChatModel):
    """Local chat model using Hugging Face transformers."""
    
    def __init__(self, model_name: str = CHAT_MODEL):
        """
        Initialize chat model. Falls back to a smaller model if the configured model fails.
        AWQ models don't work on macOS, so we use standard models instead.
        """
        # Try to load the configured model, but fall back to a smaller one if it fails
        try:
            print(f"Attempting to load model: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                low_cpu_mem_usage=True
            )
            self.model_name = model_name
        except Exception as e:
            print(f"Failed to load {model_name}: {e}")
            print("Falling back to smaller model: Qwen/Qwen2.5-0.5B-Instruct")
            fallback_model = "Qwen/Qwen2.5-0.5B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(fallback_model, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                fallback_model,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )
            self.model_name = fallback_model
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        print(f"Model loaded successfully: {self.model_name}")

    def get_response(self, prompt: str, max_new_tokens: int = 512) -> str:
        """Generate response using the loaded model."""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
            )
        
        # Decode only the generated tokens (excluding the input prompt)
        generated_text = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return generated_text.strip()
    
    def get_chat_response(self, messages: List[dict], max_new_tokens: int = 512) -> str:
        """Generate response from chat messages format."""
        # Convert messages to a single prompt
        prompt = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in messages])
        return self.get_response(prompt, max_new_tokens)


class SAPAIChatModel(BaseChatModel):
    """SAP AI Core chat model using API calls."""
    
    def __init__(self, model_name: str = CHAT_MODEL_NAME):
        """Initialize SAP AI Core chat model."""
        from app.helpers.sap_ai_core_client import get_sap_ai_core_client
        
        self.client = get_sap_ai_core_client()
        self.model_name = model_name
        print(f"SAP AI Core chat model initialized: {self.model_name}")
    
    def get_response(self, prompt: str, max_new_tokens: int = 512) -> str:
        """Generate response using SAP AI Core API."""
        # Convert simple prompt to chat format
        messages = [{"role": "user", "content": prompt}]
        return self.get_chat_response(messages, max_new_tokens)
    
    def get_chat_response(self, messages: List[dict], max_new_tokens: int = 512) -> str:
        """Generate response from chat messages format."""
        return self.client.chat_completion(
            model=self.model_name,
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=0.7
        )


def create_chat_model() -> BaseChatModel:
    """Factory function to create chat model based on configuration."""
    if MODEL_PROVIDER == 'sap_ai_core':
        return SAPAIChatModel(model_name=CHAT_MODEL_NAME)
    else:
        return LocalChatModel(model_name=CHAT_MODEL)


# Global chat model instance
chat_model = create_chat_model()


def generate_response(user_message: str, user_id: str, chat_id: str) -> str:
    """
    Generate AI response using RAG context and chat history.
    """
    # Initialize
    client = QdrantClient("localhost", port=6333)
    collection_name = f"user_{user_id}_documents"
    
    # 1. Get RAG Context
    from app.helpers.embeddings import advanced_search_similar_embeddings
    
    rag_results = advanced_search_similar_embeddings(
        user_message=user_message,
        vector_db_client=client,
        collection_name=collection_name,
        similarity_threshold=0.25,
        limit=5
    )
    print(f"RAG results found: {rag_results}")
    
    # 2. Get Chat History (start with reasonable limit)
    max_history_messages = 10
    chat_history = get_chat_messages(chat_id, limit=max_history_messages)
    
    # 3. Build Prompt Components
    system_prompt = """You are a knowledgeable AI assistant answering user questions using Retrieval-Augmented Generation (RAG).

STRICT RULES:
- Answer ONLY using the information present in the Documentation Context.
- If the context does not contain sufficient information, clearly say:
  "The provided documentation does not contain enough information to answer this question."
- Do NOT use prior knowledge or make assumptions.
- If multiple sources conflict, mention the conflict explicitly.
- Be concise, accurate, and factual.

RESPONSE FORMAT (Markdown):
- Use clear section headers when appropriate
- Use bullet points for lists
- Use fenced code blocks for code
- When referencing documentation, cite it as (Source X)

You may use the Conversation History ONLY to understand intent and continuity,
NOT as a source of factual information.
"""
    
    # Format RAG context
    if rag_results:
        context_texts = [f"[Source {i+1}]: {item['payload']['chunk_text']}" 
                        for i, item in enumerate(rag_results)]
        rag_context = "\n\n".join(context_texts)
    else:
        rag_context = "No relevant documentation found."
    
    # Format chat history
    history_text = ""
    if chat_history:
        history_lines = [f"{msg['role'].upper()}: {msg['content']}" 
                        for msg in chat_history]
        history_text = "\n".join(history_lines)
    
    # 4. Build Full Prompt with Token Management
    prompt = f"""{system_prompt}

## Documentation Context
{rag_context}

## Conversation History
{history_text}

## User Question
{user_message}

## Instructions
- Base your answer strictly on the Documentation Context above
- Cite sources as (Source 1), (Source 2), etc.
- If no relevant information exists, say so explicitly

## Answer"""
    
    # 5. Trim if needed (keep most recent history)
    while len(prompt) > CHAT_MODEL_CONTEXT_LENGTH and max_history_messages > 0:
        max_history_messages -= 2  # Remove 2 messages at a time (user + assistant)
        chat_history = get_chat_messages(chat_id, limit=max_history_messages)
        
        history_text = ""
        if chat_history:
            history_lines = [f"{msg['role'].upper()}: {msg['content']}" 
                            for msg in chat_history]
            history_text = "\n".join(history_lines)
        
        prompt = f"""{system_prompt}

## Documentation Context
{rag_context}

## Conversation History
{history_text}

## User Question
{user_message}

## Instructions
- Base your answer strictly on the Documentation Context above
- Cite sources as (Source 1), (Source 2), etc.
- If no relevant information exists, say so explicitly

## Answer"""
    
    print(f"Final prompt : {prompt}, length: {len(prompt)}")
    
    # 6. Generate Response
    response = chat_model.get_response(prompt, max_new_tokens=1028)
    print("generated response:", response)
    
    return response


def generate_queries(user_message: str, queries_number: int) -> List[str]:
    """
    Generate multiple queries for the vector database.
    """
    system_prompt = f"""You are a Retrieval-Augmented Generation (RAG) query generator.

Your task:
Generate {queries_number} diverse and high-quality search queries that maximize document retrieval.

QUERY STRATEGY:
- Include both semantic and keyword-style queries
- Include acronyms, component names, and config keys when applicable
- Include error-message or log-style queries if relevant
- Prefer short, precise queries (5–12 words)

RULES:
- One query per line
- No numbering or bullet points
- No explanations
- Do NOT repeat similar queries"""
    
    prompt = f"""{system_prompt}

User question:
{user_message}

Search queries:"""
    
    response = chat_model.get_response(prompt, max_new_tokens=128)
    print("Generated queries:", response)
    return response.splitlines()
