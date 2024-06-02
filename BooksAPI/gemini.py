from typing import List

import google.generativeai as genai
import os
API_KEY = 'AIzaSyAa-wKVWaaGOPF6tszXhI-6sgu0aEDLWBQ'
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')


def getAIsummary(bookName: str, authorName: str) -> str:
    """
    This function takes a book name and an author name and returns the summary of the book from gemini pro
    :param bookName: string
    :param authorName: string
    :return:
    """
    response = model.generate_content(f'Summarize the book {bookName} by {authorName} in 5 sentences or less')
    return response.text