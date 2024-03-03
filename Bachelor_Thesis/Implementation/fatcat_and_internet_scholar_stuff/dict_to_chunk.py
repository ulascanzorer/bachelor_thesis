def chunks(input_dict: dict[str, list[int]], number_of_chunks: int) -> list[dict[str, list[int]]]:
    if number_of_chunks <= 0:
        return []

    items_list = list(input_dict.items())
    num_items = len(items_list)
    chunks = []
            
    if number_of_chunks >= num_items:
        for i in range(0, num_items):
            chunks.append(dict(items_list[i : i + 1]))
        for i in range(0, number_of_chunks - num_items):
            chunks.append({})
        return chunks

    if number_of_chunks == 1:
        chunks.append(input_dict)
        return chunks

    standard_chunk_size = num_items // number_of_chunks
    final_chunk_size = standard_chunk_size + (num_items % number_of_chunks)

    for i in range(0, num_items, standard_chunk_size):
        if i + final_chunk_size == num_items:
            chunks.append(dict(items_list[i : num_items]))
            return chunks
        chunks.append(dict(items_list[i : i + standard_chunk_size]))
    
    return chunks
