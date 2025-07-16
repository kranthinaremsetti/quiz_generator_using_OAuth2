from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser


def generate_quiz(topic, api_key, num_mcq=5, num_fill=2, difficulty="Medium"):
    """
    Generate quiz questions using Google's Gemini AI.
    
    Args:
        topic (str): The topic or content for quiz generation
        api_key (str): Google API key for Gemini
        num_mcq (int): Number of multiple choice questions
        num_fill (int): Number of fill-in-the-blank questions
        difficulty (str): Difficulty level (Easy, Medium, Hard)
        
    Returns:
        dict: Generated quiz with 'mcq' and 'fill' question arrays
    """
    parser = JsonOutputParser()
    prompt = PromptTemplate(
        template="""
        You are a quiz generator bot. The content below contains information from multiple sources/files and a user prompt.

        USER PROMPT (from the educator):
        {user_prompt}

        IMPORTANT: Generate questions that draw content from ALL the provided sources equally. Do not focus only on the first section or only on the user prompt.

        Generate {num_mcq} multiple-choice questions (MCQs) and {num_fill} fill-in-the-blank questions (FIBs).

        Each MCQ must include:
        - 'question'
        - 'options' (list of {num_options} choices)
        - 'answer' (one correct option)

        Each FIB must include:
        - 'question' with blank(s)
        - 'answer' (expected fill)

        Make sure all questions are of **{difficulty}** difficulty level.

        ENSURE BALANCED COVERAGE: If multiple files/sections are provided, create questions from each section and the user prompt proportionally.

        Content from multiple sources:
        {topic}

        Respond in valid JSON format with two keys: 'mcq' and 'fill'.

        {format_instructions}
        """,
        input_variables=["topic", "user_prompt", "num_mcq", "num_fill", "difficulty", "num_options"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.7
    )

    chain = prompt | llm | parser

    # Accept num_options as an argument, default to 4 for backward compatibility
    def invoke_with_options(user_prompt, num_options=4):
        return chain.invoke({
            "topic": topic,
            "user_prompt": user_prompt,
            "num_mcq": num_mcq,
            "num_fill": num_fill,
            "difficulty": difficulty,
            "num_options": num_options
        })

    return invoke_with_options
