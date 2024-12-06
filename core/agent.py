import ast
import io
import json
import logging
import re
import sys
from functools import partial

import numpy as np
import openai
import pandas as pd
from langchain.agents import AgentExecutor, Tool
from langchain.agents.react.agent import create_react_agent
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain_experimental.utilities.python import PythonREPL
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from core.data_processing import DataProcessor
from core.langchain_client import get_llm, get_prompt
from core.visualizations import VisualizationGenerator

# Configure the logging
logging.basicConfig(
    level=logging.INFO,  # Set the level to INFO or DEBUG to see more logs
    format="%(asctime)s [%(levelname)s] %(message)s",  # Add a timestamp and level to log messages
    handlers=[logging.StreamHandler()],  # Log to console
)
logger = logging.getLogger(__name__)

# Initialize DataProcessor and VisualizationGenerator
data_processor = DataProcessor()
visualization_generator = VisualizationGenerator()


def clean_code(input_str):

    # Extract dictionary-like content from the cleaned string
    match = re.search(r"summary\s*=\s*{(.*)}", input_str, flags=re.DOTALL)
    if match:
        # Extract the dictionary content
        dict_content = match.group(1)

        # Remove extra newlines and spaces
        dict_content = re.sub(r"\s+", " ", dict_content).strip()

        # Step 4: Optionally, extract values from the dictionary (if needed)
        dict_values = []
        dict_entries = re.findall(
            r"'(\w+)'\s*:\s*(\S+)", dict_content
        )  # Match key-value pairs

        for _, value in dict_entries:  # Ignore the key and take only the value
            dict_values.append(value)  # Append only the value to the list

        # Return the list of values and the Python code blocks as separate results
        return dict_values
    else:
        return input_str


# Generalized query-to-code agent
def query_to_code_agent(input_text: str, data_id: str) -> str:
    """
    Converts user query into Python code.
    """
    logger.info(f"Received user query: {input_text}")

    try:
        data = data_processor.get_data_by_id(data_id)
        if data is not None:
            columns = list(data.columns)  # Get the column names
            logger.info(f"Data loaded successfully, columns found: {columns}")
        else:
            logger.error(f"No data found for data_id: {data_id}")
            return "Error: Dataset not found."

        logger.info("Converting user query to Python code.")
        llm = get_llm()
        prompt = (
            "\You are the expert data analyst with 5 year of experience. Your job is to take a User query and"
            "understand it sementic meaning and then generate Python code that can be executed on the dataset to provide an answer. "
            "The code you generate should **only** contain the Python code needed to execute the task, with no extra explanations or formatting. "
            "The response should **only** be the Python code, formatted as it would appear in a script, with no additional text. For example, if the user asks for "
            "the number of rows and columns, return only the Python code like this: `data.shape[0], data.shape[1]`."
            "Only return the code in string format  within ```python ```. Do not add the comment, variable and extra/additional text in response only simple code.\n\n"
            "Context:\n"
            "- The dataset is a pandas DataFrame called 'data'.\n"
            f"- The dataset has the following columns: {columns}.\n\n"
            "Here are a few examples of user queries and the expected Python code response:\n"
            "Example 1: User Query: 'What does the data look like?'\n"
            "Python Code: data.head()\n\n"
            "Example 2: User Query: 'Show me the first few rows of the data.'\n"
            "Python Code: data.head()\n\n"
            "Example 3: User Query: 'What are the main statistics of this data?'\n"
            "Python Code: data.describe()\n\n"
            "Example 4: User Query: 'How many columns and rows are in the dataset?'\n"
            "Python Code: data.shape[0], data.shape[1]\n\n"
            "Example 5: User Query: 'Tell me the types of data in each column.'\n"
            "Python Code: data.dtypes \n\n"
            "Example 6: User Query: 'Show me if there are any missing values in the dataset.'\n"
            "Python Code: data.isnull().sum()\n\n"
            "Example 6: User Query: ' Provide a detailed analysis of the dataset, including summary statistics, missing values, and significant trends or insights..'\n"
            "Python Code: data.isnull().sum(), data.describe(), data.corr()\n\n"
            f"User Query: {input_text}\n\n"
            "Python Code:"
        )

        logger.debug(f"Prompt sent to LLM: {prompt}")
        response = llm.invoke(prompt)
        python_code = response.content
        logger.info(f"Generated Python code:\n{python_code}")

        return python_code
    except Exception as e:
        logger.error(f"Error in query_to_code_agent: {str(e)}")
        return f"Error: {str(e)}"


def validate_python_code(python_code: str) -> bool:
    """
    Validates the Python code by attempting to parse it using AST.
    """
    logger.info(
        f"Validating Python code:\n{python_code[:100]}..."
    )  # Log first 100 chars for readability

    try:
        # Strip leading/trailing whitespace
        python_code = python_code.strip()

        # Basic check for empty code
        if not python_code:
            logger.error("Empty code provided.")
            return False

        # # Check for unbalanced parentheses, brackets, and braces
        # if not are_parentheses_balanced(python_code):
        #     logger.error("Unbalanced parentheses or brackets detected.")
        #     return False

        # # Check for unclosed strings
        # if not are_strings_closed(python_code):
        #     logger.error("Unclosed string detected.")
        #     return False

        # # Check for valid indentation
        # if not is_indentation_valid(python_code):
        #     logger.error("Invalid indentation detected.")
        #     return False

        # Try parsing the code into an AST
        ast.parse(python_code)
        logger.info("Python code validated successfully.")
        return True
    except SyntaxError as e:
        logger.error(f"Syntax error in code: {e}")
        return False
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return False


def are_parentheses_balanced(code: str) -> bool:
    """
    Check if parentheses, brackets, and braces are balanced in the given Python code.
    """
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}

    for char in code:
        if char in "({[":
            stack.append(char)
        elif char in ")}]":
            if not stack or stack.pop() != pairs[char]:
                logger.error(f"Unbalanced parentheses/brackets detected: {char}")
                return False
    if stack:
        logger.error(f"Unbalanced parentheses/brackets detected: {stack}")
    return not stack  # Stack should be empty if balanced


def are_strings_closed(code: str) -> bool:
    """
    Check if all strings in the code are properly closed.
    """
    in_string = False
    quote_char = None

    for char in code:
        if char in ('"', "'"):
            if in_string:
                if char == quote_char:  # Closing the string
                    in_string = False
                    quote_char = None
            else:
                in_string = True
                quote_char = char  # Opening a new string
    if in_string:
        logger.error("Unclosed string detected.")
    return not in_string  # Should be closed if no string is left open


def is_indentation_valid(code: str) -> bool:
    """
    Check if indentation follows Python's indentation rules.
    """
    lines = code.splitlines()
    for line in lines:
        if line != line.strip():  # If line has indentation
            if "\t" in line:
                logger.error("Tab characters detected. Use spaces for indentation.")
                return False
    logger.info("Indentation is valid.")
    return True


def format_python_code(python_code: str) -> str:
    """
    Ensures that Python code is correctly formatted.
    """
    try:
        formatted_code = python_code.strip()
        logger.info(f"Formatted code:\n{formatted_code}")
        return formatted_code
    except Exception as e:
        logger.error(f"Error formatting Python code: {e}")
        return python_code


def capture_output(func):
    """
    Captures the printed output of a function.
    """
    captured_output = io.StringIO()  # Create a string buffer
    sys.stdout = captured_output  # Redirect stdout to the buffer
    sys.stderr = captured_output  # Redirect stderr to the buffer

    try:
        func()  # Execute the function
    except Exception as e:
        captured_output.write(f"Error: {str(e)}")  # Capture error if occurs
    finally:
        sys.stdout = sys.__stdout__  # Reset redirect.
        sys.stderr = sys.__stderr__  # Reset redirect.

    return captured_output.getvalue()  # Return captured output


def check_and_preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Checks if the DataFrame has empty data and preprocesses it (removes nulls, duplicates, etc.),
    including handling missing values, converting categorical data to numeric, and standardizing columns.

    Args:
        df (pd.DataFrame): The loaded dataframe.

    Returns:
        pd.DataFrame: The cleaned and preprocessed dataframe.
    """
    # Check if DataFrame is empty
    try:
        if df.empty:
            logger.warning("The DataFrame is empty.")
            return df  # Return the empty DataFrame if it is empty

        # Check if DataFrame is empty (only NaNs)
        if df.isnull().all().all():
            logger.warning("The DataFrame contains only null values.")
            return df.dropna(how="all")  # Drop all rows that are completely null

        # Check for empty rows (rows where all columns are NaN)
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            logger.info(f"Found {empty_rows} empty rows. Dropping them.")
            df = df.dropna(how="all")

        # Remove any rows with duplicate data
        duplicate_rows = df.duplicated().sum()
        if duplicate_rows > 0:
            logger.info(f"Found {duplicate_rows} duplicate rows. Dropping them.")
            df = df.drop_duplicates()

        # Handle missing data using an imputer (mean for numeric, most frequent for categorical)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=[object]).columns

        logger.debug(f"Numeric columns: {numeric_cols}")
        logger.debug(f"Categorical columns: {categorical_cols}")

        # Impute numeric columns with mean, if they are not empty
        if len(numeric_cols) > 0:
            logger.debug("Imputing missing values for numeric columns.")
            imputer_numeric = SimpleImputer(strategy="mean")
            df[numeric_cols] = imputer_numeric.fit_transform(df[numeric_cols])
        else:
            logger.debug("No numeric columns found for imputation.")

        # Impute categorical columns with the most frequent value (mode), if they are not empty
        if len(categorical_cols) > 0:
            logger.debug("Imputing missing values for categorical columns.")
            imputer_categorical = SimpleImputer(strategy="most_frequent")
            df[categorical_cols] = imputer_categorical.fit_transform(
                df[categorical_cols]
            )
        else:
            logger.debug("No categorical columns found for imputation.")

        # Encode categorical columns (if any) to numeric (Label Encoding)
        if len(categorical_cols) > 0:
            label_encoder = LabelEncoder()
            for col in categorical_cols:
                if df[col].dtype == "object":  # If the column is categorical
                    logger.debug(f"Label encoding column: {col}")
                    df[col] = label_encoder.fit_transform(df[col].astype(str))
        else:
            logger.debug("No categorical columns to encode.")

        # Convert columns to appropriate types (e.g., date columns)
        for col in df.select_dtypes(include=[object]).columns:
            try:
                # Try to convert to datetime
                logger.debug(f"Attempting to convert column '{col}' to datetime.")
                df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
            except Exception as e:
                logger.error(
                    f"Column '{col}' could not be converted to datetime: {str(e)}"
                )

        # Handle remaining missing values (if any) by forward filling or drop if too many missing values
        df = df.ffill()  # Forward fill missing data as an example

        # Optional: Remove rows or columns if too many missing values
        threshold = 0.5  # e.g., remove columns with more than 50% missing values
        df = df.dropna(
            thresh=int(threshold * len(df)), axis=1
        )  # Drop columns with too many missing values
        df = df.dropna(
            how="any"
        )  # Drop any rows that still have missing values after filling

        logger.info(
            f"Data after preprocessing: {df.shape} rows and {df.shape[1]} columns."
        )
        return df
    except Exception as e:
        logger.info(f" the errro in check and preprocess: {e}")


def analytic_agent(user_input: str, data_id: str, data_name: str) -> str:
    """
    Executes Python code based on user input.
    """
    logger.info(f"Starting code execution for query: {user_input}")

    try:
        logger.info("entering analtic agent")
        python_code = query_to_code_agent(user_input, data_id)
        # logger.info(f"python code: {type(python_code)}")
        python_code_blocks = re.findall(
            r"```(?:python)?(.*?)```", python_code, flags=re.DOTALL
        )
        if python_code_blocks:
            logger.info(f"python code: {type(python_code_blocks)}")
            logger.info(f"python code: {python_code_blocks}")
            # clean_pythona_code = clean_code(str(python_code_blocks))
            # logger.info(f"clean python code: {clean_pythona_code}")
            # Step 1: Remove newlines from the string
            python_code = "".join(python_code_blocks).replace("\n", " ").strip()
        else:
            python_code = "".join(python_code).replace("\n", " ").strip()
        logger.info(f"python code: {python_code}")
        # Step 2: Use regular expression to split on commas before data functions but avoid splitting inside them
        steps = re.split(r"(?<=\)),\s*(?=data\.)", python_code)
        logger.info(f"before steps clean: {steps}")

        if steps:
            # Clean up the list to remove any empty strings or leading/trailing spaces
            steps = [step.strip() for step in steps if step.strip()]
            logger.info(f"after steps clean: {steps}")
        else:
            steps = python_code
        results = []  # Collect results of each execution step

        logger.info(f"Steps to execute: {steps}")

        for step in steps:
            step = step.strip()  # Clean up the step

            if step:
                # # Validate the code first
                # logger.info(f"Validating code: {step}")
                # if not validate_python_code(step):
                #     results.append(f"Invalid code: {step}")
                #     continue  # Skip execution if the code is invalid

                # # Format the Python code before execution
                # formatted_code = format_python_code(step)

                try:
                    logger.info(f"Executing formatted code: {step}")

                    # Get the dataset
                    data_file_path = data_processor.get_file_path_by_id(data_id)
                    data = data_processor._load_dataframe(data_file_path)
                    if data is None:
                        logger.error(f"Dataset with ID {data_id} not found.")
                        results.append(f"Dataset with ID {data_id} not found.")
                        continue
                    logger.info(f"dataset are: {data}")

                    globals_dict = {"data": data}
                    locals_dict = {}
                    code = f"result={step}"
                    # Use exec to run the code in a custom context
                    exec(code, globals_dict, locals_dict)
                    # logger.info(exec(step, {}, local_vars))
                    logger.info(f"local vars: {locals_dict}")
                    result = locals_dict.get("result", None)
                    logger.info(f"result are: type{type(result)}")
                    if (
                        isinstance(result, pd.Series)
                        or isinstance(result, pd.DataFrame)
                        or isinstance(result, pd.Index)
                    ):
                        if isinstance(result, pd.Series):
                            result = result.to_frame()  # Convert Series to DataFrame
                            logger.info("Converted Series to DataFrame.")

                        elif isinstance(result, pd.Index):
                            result = result.to_frame(
                                name="index"
                            )  # Convert Index to DataFrame with column name 'index'
                            logger.info("Converted Index to DataFrame.")

                        if not result.empty:
                            logger.info("fffffffffffffffffffff")
                            output = result
                    elif (
                        isinstance(result, list)
                        or isinstance(result, tuple)
                        or isinstance(result, dict)
                        or isinstance(result, float)
                        or isinstance(result, str)
                        or isinstance(result, int)
                        or isinstance(result, bool)
                        or isinstance(result, set)
                    ):
                        if result:
                            logger.info("KKKKKKKKKKKKKKK")
                            output = result
                    elif isinstance(result, np.ndarray):
                        logger.info("MMMMMMMMMMMMMMMMMMMMMM")
                        output = eval(step, globals_dict, locals_dict)
                    else:
                        logger.info("ddddddddddddddddddddd")
                        output = capture_output(
                            lambda: exec(python_code, globals_dict, locals_dict)
                        )
                        logger.info(f"output: {output}")
                    logger.info(f"output of query: {output}")
                    results.append(str(output))  # Capture printed output
                    # else:
                    #     # Execute the Python code normally and capture result
                    #     local_vars = {"data": data}
                    #     exec(formatted_code, {}, local_vars)
                    #     result = local_vars.get("result", None)  # Capture the result
                    #     if result is not None:
                    #         logger.info(f"Execution result: {result}")
                    #         results.append(str(result))  # Collect result
                    #     else:
                    #         results.append(f"No result found for: {step}")

                except Exception as e:
                    logger.error(f"Error executing step '{step}': {e}")
                    results.append(f"Error executing step '{step}': {str(e)}")

        # Return the combined results after all steps

        final_results = "\n".join(results)
        logger.info(f"Execution results: {final_results}")
        llm = get_llm()
        prompt = f"""User Input: {user_input}\n\nExecution Results: {final_results}\n\nBased on this information,
                    Understand the exceution result based on the user input. THten generate the response in a simple language"""

        response_i = llm.invoke(prompt)
        response = response_i.content
        logger.info(f"response: {response}")
        return response

    except Exception as e:
        logger.error(f"Error in code_execution_agent: {str(e)}")
        return f"Error: {str(e)}"


def analyze_query_with_llm(query: str, columns: list) -> dict:
    """
    Use OpenAI's LLM to analyze the query and extract plot type and column(s).
    If the plot type or column is not explicitly mentioned, defaults are applied.
    """
    logger.info("Analyzing user query with OpenAI LLM.")
    prompt = f"""
    You are an AI assistant helping to generate data visualizations. Given a user's query and the available columns in the dataset,
    extract the type of plot the user wants and the column(s) involved. If no specific plot type is mentioned, choose a general one.
    Available columns: {columns}.
    User query: "{query}"
    Respond with a JSON object containing:
    - "plot_type": The type of plot (e.g., bar, line, scatter, pie, histogram).
    - "columns": A list of relevant columns (default to the first column if none are specified).
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        llm_response = response["choices"][0]["message"]["content"]
        result = json.loads(llm_response)
        logger.info(f"LLM response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error during LLM query analysis: {e}")
        # Fallback to default values
        return {"plot_type": "bar", "columns": [columns[0]] if columns else []}


def preprocess_data(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Preprocess the DataFrame before visualization.
    """
    logger.info("Preprocessing data before visualization.")

    # Handle missing values
    df = df.fillna(method="ffill").fillna(method="bfill")
    df = df.apply(lambda col: col.interpolate() if col.dtype == np.float64 else col)
    df = df.fillna(df.mean(numeric_only=True))

    # Ensure correct data types
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype("category")

    # Extract plot type and column(s) using LLM
    columns = list(df.columns)
    query_analysis = analyze_query_with_llm(query, columns)
    plot_type = query_analysis.get("plot_type", "bar")
    relevant_columns = query_analysis.get("columns", [])

    # If no relevant columns are found, assume all columns in the dataset
    if not relevant_columns:
        logger.info(
            "No specific columns found in the query. Assuming all columns in the dataset."
        )
        relevant_columns = columns

    # Validate and convert relevant columns to numeric
    valid_columns = []
    for column in relevant_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
            valid_columns.append(column)
        else:
            logger.warning(f"Column '{column}' not found in dataset. Skipping.")

    if not valid_columns:
        logger.warning(
            "No valid columns available for plotting. Skipping visualization."
        )
        return

    # Scale numerical columns
    if plot_type in ["scatter", "line"]:
        numeric_cols = df.select_dtypes(include=np.number).columns
        if len(numeric_cols) > 1:
            scaler = StandardScaler()
            df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

    # If the plot type requires only one column (e.g., scatter, line), generate a plot for each column
    if plot_type in ["scatter", "line"] and len(valid_columns) > 1:
        logger.info(
            f"Plot type '{plot_type}' requires one column. Generating plots for each valid column."
        )
        for column in valid_columns:
            logger.info(f"Generating {plot_type} plot for column '{column}'.")
            # Call the plotting function for each column
            visualization_generator.generate_plot(
                df[[column]], query=f"{plot_type} plot for {column}"
            )
    else:
        # For other plot types or if one column is sufficient, generate a single plot
        logger.info(f"Generating {plot_type} plot for columns: {valid_columns}.")
        visualization_generator.generate_plot(df[valid_columns], query=query)

    # Remove duplicates and constant columns
    df = df.drop_duplicates()
    df = df.loc[:, (df.nunique() > 1)]

    logger.info("Preprocessing completed.")
    return df


def visualization_agent(query: str, data_id: str) -> str:
    """
    Generates a visualization based on the user's query and returns the image as a base64 string.
    """
    logger.info(
        f"Generating visualization for query: '{query}' using dataset ID: {data_id}."
    )

    # Retrieve data by data_id
    data_file_path = data_processor.get_file_path_by_id(data_id)
    data = data_processor._load_dataframe(data_file_path)
    if data is None:
        logger.error(f"Dataset with ID {data_id} not found.")
        return f"Error: Dataset with ID {data_id} not found."

    try:
        # Preprocess the data
        preprocessed_data = preprocess_data(data, query)

        # Generate the plot using VisualizationGenerator
        img_base64 = visualization_generator.generate_plot(
            preprocessed_data, query=query
        )

        if "Error:" in img_base64:
            logger.error(f"Error during visualization generation: {img_base64}")
            return img_base64

        logger.info("Visualization generated successfully.")
        return img_base64

    except Exception as e:
        logger.error(f"Unexpected error generating visualization: {e}")
        return f"Error: Unexpected error generating visualization. Details: {str(e)}"


# Dataset info agent
def dataset_info_agent(input_text: str = "") -> str:
    """
    Returns information about available datasets.
    """
    logger.info(
        f"Received request for dataset information. Input query: {data_processor.data_store}"
    )

    try:
        if not data_processor.data_store:
            logger.warning("No datasets are currently available.")
            return (
                "No datasets are currently available. Please upload a dataset to begin."
            )

        logger.info("Fetching dataset information from data store.")
        dataset_info = "\n".join(
            [
                f"ID: {data_id}, Shape: {df.shape}, Columns: {list(df.columns)}, Describe:{df.describe()}, Summary:{df.info()}, Correlation:{df.corr()}"
                for data_id, df in data_processor.data_store.items()
            ]
        )

        logger.info(f"Dataset information retrieved successfully. {dataset_info}")
        return f"Available information about data:\n{dataset_info}"

    except Exception as e:
        logger.error(f"Error fetching dataset information: {str(e)}")
        return f"Error occurred while fetching dataset information: {str(e)}"


# Define the conversation tool
def conversation_tool(query: str) -> str:
    """
    Handle the conversation by sending the user's input and the conversation context
    to the LLM, and return the generated response.
    """
    logger.info(f"Received user query for conversation: {query}")

    try:
        # Get the LLM (Large Language Model) for generating a response
        llm = get_llm()

        logger.info("Preparing the conversation prompt for LLM.")
        prompt = f"""
        You are a friendly data analytics assistant named KynAI. Here is the context of the conversation so far:

        Now, respond to the user query:
        {query}
        """

        logger.debug(f"Prompt sent to LLM: {prompt}")

        # Invoke the LLM to generate a response
        response = llm.invoke(prompt)
        result = response.content

        logger.info("LLM response generated successfully.")
        return result

    except Exception as e:
        logger.error(f"Error during conversation handling: {str(e)}")
        return f"Error occurred while processing your request: {str(e)}"


# Combined agent setup
def get_combined_agent(data_id: str):
    # Retrieve the dataset by ID
    data = data_processor.get_data_by_id(data_id)
    data_name = data_processor.get_filename_by_id(data_id)
    if data is None:
        raise ValueError(f"Dataset with ID {data_id} not found.")

    # Initialize Python REPL with the dataset
    repl = PythonREPL(globals={"data": data})
    python_repl_tool = PythonREPLTool(
        python_repl=repl,
        name="Python REPL",
        description="Execute Python commands on the dataset 'data'.",
    )

    # Define tools with descriptions
    tools = [
        # Tool(
        #     name="Query to Code Tool",
        #     func=partial(query_to_code_agent, data_id=data_id),
        #     description="Converts user queries into Python code that operates on the dataset.",
        # ),
        Tool(
            name="data analytic Tool",
            func=partial(analytic_agent, data_id=data_id, data_name=data_name),
            description="Provide the data analysisi result based on user input given to you.",
        ),
        # Tool(
        #     name="Visualization Tool",
        #     func=partial(visualization_agent, data_id=data_id),
        #     description="Generates visualizations by executing Python code on the dataset.",
        # ),
        Tool(
            name="Conversation Tool",
            func=conversation_tool,  # Placeholder for now, will update later with main agent logic
            description="Handles user queries like some example('hello', how are you doing, what's up, bye , good night, etc) conversationally using the main agent executor.",
        ),
    ]

    # Get LLM and prompt for React agent
    llm = get_llm()
    prompt = get_prompt()
    # Create the agent using the tools and prompt
    react_agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # Wrap the agent with AgentExecutor
    agent_executor = AgentExecutor(
        agent=react_agent,
        tools=tools,
        max_execution_time=30,
        verbose=True,  # Enable detailed logs
        handle_parsing_errors=True,  # Stop after generating a valid response
    )

    logging.info(f"Agent initialized: {agent_executor}")

    return agent_executor
