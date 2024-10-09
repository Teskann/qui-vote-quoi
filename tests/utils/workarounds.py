def find_all_next_fixed(item, name, string):
    """
    Fixes the behavior of BeautifulSoup find_all_next that sometimes doesn't find
    the correct items
    """
    all_next = item.find_all_next(name)
    result = []
    for next_element in all_next:
        if string.match(next_element.text):
            result.append(next_element)
    return result

def find_all_fixed(item, name, string):
    """
    Fixes the behavior of BeautifulSoup find_all that sometimes doesn't find
    the correct items
    """
    all_next = item.find_all(name)
    result = []
    for next_element in all_next:
        if string.match(next_element.text):
            result.append(next_element)
    return result

def find_all_previous_fixed(item, name, string):
    """
    Fixes the behavior of BeautifulSoup find_all_previous that sometimes doesn't find
    the correct items
    """
    all_next = item.find_all_previous(name)
    result = []
    for next_element in all_next:
        if string.match(next_element.text):
            result.append(next_element)
    return result