from typing import Callable

def gender_from_name(name: str, gender_api: Callable[[str], str]) -> str:
    """
    Attempts to return the gender from a name in the database

    :param name: target name
    :return: guessed gender of the target name
    """

    name_parts = name.split()

    # Check if the first name(s) are abbreviated (Case 1).
    if len(name_parts[0]) == 1 or name_parts[0][1] == ".":
        return "unknown"

    # Return unknown for multiple names (Case 4).
    for part in name_parts:
        if "," in part:
            return "unknown"

    # Rest of the cases.
    first_part = name_parts[0]
    last_part = name_parts[len(name_parts) - 1]

    guessed_gender = gender_api(first_part)

    if guessed_gender != "unknown":
        if guessed_gender == "andy":
            return "male/female"
        return guessed_gender
    
    guessed_gender = gender_api(last_part)

    if guessed_gender == "andy":
        return "male/female"

    return guessed_gender