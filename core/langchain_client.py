import logging
import os

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Configure the logging
logging.basicConfig(
    level=logging.INFO,  # Set the level to INFO or DEBUG to see more logs
    format="%(asctime)s [%(levelname)s] %(message)s",  # Add a timestamp and level to log messages
    handlers=[logging.StreamHandler()],  # Log to console
)
logger = logging.getLogger(__name__)


# Initialize OpenAI LLM
def get_llm():
    """
    Returns an OpenAI LLM client with the provided API key.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"api key : {api_key}")
    if api_key:
        try:
            return ChatOpenAI(
                model="gpt-4o",
                api_key=api_key,
            )
        except Exception as e:
            logger.info(f"Error initializing the LLM: {e}")
            return None
    else:
        logger.info("API key is missing.")
        return None


def get_prompt():
    return PromptTemplate(
        input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
        template=(
            """You are the expert data analyst named as KynAI. 
            You have dataset that have name store in data_name.
            Response always be in well structure format with markdowns and also explain the meaning ofresponse in simple and interective way.
            You have access to the following tools:
            ** Available tool are**
            {tools}

            Use the following format:

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question (keep the tool response as final response in well structured format)

            Begin!

            Question: {input}
            Thought:{agent_scratchpad}"""
        ),
    )
