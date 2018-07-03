#-*- coding: utf-8 -*-

import re


BlankCharSet = set([' ', '\n', '\t'])
CommaNumberPattern = re.compile(u'\d{1,3}([,，]\d\d\d)+')
CommaCharInNumberSet = set([',', '，'])
NumberSet = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.'])


def clean_text(text):
    return clean_number_in_text(remove_blank_chars(text))


def clean_number_in_text(text):
    comma_numbers = CommaNumberPattern.finditer(text)
    new_text, start = [], 0
    for comma_number in comma_numbers:
        new_text.append(text[start:comma_number.start()])
        start = comma_number.end()
        new_text.append(remove_comma_in_number(comma_number.group()))
    new_text.append(text[start:])
    return ''.join(new_text)


def remove_blank_chars(text):
    new_text = []
    if text is not None:
        for ch in text:
            if ch not in BlankCharSet:
                new_text.append(ch)
    return ''.join(new_text)


def remove_comma_in_number(text):
    new_text = []
    if text is not None:
        for ch in text:
            if ch not in CommaCharInNumberSet:
                new_text.append(ch)
    return ''.join(new_text)

def extract_number(text):
    new_text = []
    for ch in text:
        if ch in NumberSet:
            new_text.append(ch)
    return ''.join(new_text)

if __name__ == "__main__":
    text = "总股 2,000,000 总价 300,000,000,000 元"
    print(text)
    print(clean_number_in_text(text))
