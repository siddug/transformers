
# Given a piece of text, max chunk size, chunk it into smaller pieces and return the chunks
# Implement different chunking strategies
# naive chunking - chunk based on max chunk token size
# sentence chunking - chunk based on sentence boundaries (with fall back to naive chunking for larger sentences)
# paragraph chunking - chunk based on paragraph boundaries (with fall back to sentence boundaries for larger paragraphs)
# contextual chunking - if a summary is provided, then prepend this to every chunk (with paragraph chunking as the base)
# LATER - if we can use LLMs, then we can ask them to give a better split of the text into contextually relevant chunks
# LATER - skipping overlap between chunks

import tiktoken
import nltk
nltk.download('punkt_tab')

def _convert_to_tokens(text: str, model_or_encoding: str):
    """
    Convert the text to tokens using the tiktoken library
    """
    # Check if it's an encoding name (like o200k_base, cl100k_base) or a model name
    if model_or_encoding in ["o200k_base", "cl100k_base", "p50k_base", "r50k_base"]:
        encoding = tiktoken.get_encoding(model_or_encoding)
    else:
        encoding = tiktoken.encoding_for_model(model_or_encoding)
    return encoding.encode(text)

def _convert_to_text(tokens: list[int], model_or_encoding: str):
    """
    Convert the tokens to text using the tiktoken library
    """
    # Check if it's an encoding name (like o200k_base, cl100k_base) or a model name
    if model_or_encoding in ["o200k_base", "cl100k_base", "p50k_base", "r50k_base"]:
        encoding = tiktoken.get_encoding(model_or_encoding)
    else:
        encoding = tiktoken.encoding_for_model(model_or_encoding)
    return encoding.decode(tokens)

def naive_chunking(text: str, max_chunk_size: int, model: str):
    """
    Chunk the text into smaller pieces based on the max chunk size
    """
    tokens = _convert_to_tokens(text, model)

    return [_convert_to_text(tokens[i:i+max_chunk_size], model) for i in range(0, len(tokens), max_chunk_size)]

def sentence_chunking(text: str, max_chunk_size: int, model: str):
    """
    We go through the input text sentence by sentence
    If the sentence is larger than the max chunk size, we split it into smaller chunks using naive chunking
    """
    sentences = nltk.sent_tokenize(text)
    chunks = []
    current_chunk = ""
    current_chunk_tokens = 0
    for sentence in sentences:
        tokens = _convert_to_tokens(sentence, model)
        if current_chunk_tokens + len(tokens) > max_chunk_size:
            if current_chunk_tokens > max_chunk_size:
                chunks.extend(naive_chunking(current_chunk, max_chunk_size, model))
            else:
                chunks.append(current_chunk)
            current_chunk = ""
            current_chunk_tokens = 0
        current_chunk += (" " if current_chunk else "") + sentence
        current_chunk_tokens += len(tokens)
    if current_chunk:
        if current_chunk_tokens > max_chunk_size:
            chunks.extend(naive_chunking(current_chunk, max_chunk_size, model))
        else:
            chunks.append(current_chunk)
    return chunks

def paragraph_chunking(text: str, max_chunk_size: int, model: str):
    """
    Define paragraph as a sequence of sentences separated by two newlines
    If the paragraph is larger than the max chunk size, we split it into smaller chunks using sentence chunking
    """
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = ""
    current_chunk_tokens = 0
    for paragraph in paragraphs:
        tokens = _convert_to_tokens(paragraph, model)
        if current_chunk_tokens + len(tokens) > max_chunk_size:
            if current_chunk_tokens > max_chunk_size:
                chunks.extend(sentence_chunking(current_chunk, max_chunk_size, model))
            else:
                chunks.append(current_chunk)
            current_chunk = ""
            current_chunk_tokens = 0
        current_chunk += ("\n\n" if current_chunk else "") + paragraph
        current_chunk_tokens += len(tokens)
    if current_chunk:
        if current_chunk_tokens > max_chunk_size:
            chunks.extend(sentence_chunking(current_chunk, max_chunk_size, model))
        else:
            chunks.append(current_chunk)
    return chunks


def contextual_chunking(text: str, max_chunk_size: int, model: str, summary: str):
    """
    Chunk the text into smaller pieces based on paragraph boundaries
    For every chunk, prepend the summary to the chunk
    """
    summary_tokens = _convert_to_tokens(summary, model)
    summary_tokens_length = len(summary_tokens)

    if summary_tokens_length > max_chunk_size:
        # ignore the summary or raise an error. ignore for now
        summary = ""
        summary_tokens_length = 0

    chunks = paragraph_chunking(text, max_chunk_size - summary_tokens_length, model)

    return [summary + "\n\n" + chunk for chunk in chunks]
