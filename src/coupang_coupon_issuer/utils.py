import unicodedata

def get_visual_width(text):
    """문자열의 실제 출력 너비를 계산합니다."""
    if not isinstance(text, str):
        text = str(text)
    width = 0
    for char in text:
        # 동아시아 너비 규격에 따라 'W'(Wide)나 'F'(Fullwidth)는 2칸, 나머지는 1칸
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def kor_align(text, width, align='>'):
    """한글 너비를 고려하여 정렬된 문자열을 반환합니다."""
    if not isinstance(text, str):
        text = str(text)
    visual_width = get_visual_width(text)
    padding = max(0, width - visual_width)
    
    if align == '>': # 우측 정렬
        return " " * padding + text
    elif align == '<': # 좌측 정렬
        return text + " " * padding
    else: # 가운데 정렬
        left = padding // 2
        right = padding - left
        return " " * left + text + " " * right
