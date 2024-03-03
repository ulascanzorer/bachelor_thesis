def get_chunks_from_list_chunk_size(list_input: list[any], chunk_size: int) -> list[list[any]]:
    list_size = len(list_input)
    resulting_list = []

    index = 0
    while True:
        if index > list_size - 1:
            # end of the list
            break
        
        if (index + chunk_size) > list_size:
            # we are at the last chunk, must be smaller than chunk_size
            resulting_list.append(list_input[index : list_size])
            break

        # we are at a place where we can get a chunk as big as the specified chunk_size
        resulting_list.append(list_input[index : index + chunk_size])
        index += chunk_size
    
    return resulting_list

def get_chunks_from_list_chunk_num(list_input: list[any], chunk_num: int = 1) -> list[list[any]]:
    list_size = len(list_input)
    resulting_list = []

    if chunk_num <= 0:
        return resulting_list
    elif chunk_num > list_size:
        return [[element] for element in list_input]

    standard_chunk_size = list_size // chunk_num
    final_chunk_size = standard_chunk_size + (list_size % chunk_num)

    for i in range(0, list_size, standard_chunk_size):
        if i + final_chunk_size == list_size:
            resulting_list.append(list_input[i : list_size])
            return resulting_list
        resulting_list.append(list_input[i : i + standard_chunk_size])

    return resulting_list