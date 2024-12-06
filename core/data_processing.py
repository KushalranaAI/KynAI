import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pandas as pd

# Configure the logging
logging.basicConfig(
    level=logging.INFO,  # Set the level to INFO or DEBUG to see more logs
    format="%(asctime)s [%(levelname)s] %(message)s",  # Add a timestamp and level to log messages
    handlers=[logging.StreamHandler()],  # Log to console
)
logger = logging.getLogger(__name__)


class DataFrameWrapper:
    def __init__(self, id, dataframe, filename):
        self.id = id
        self.dataframe = dataframe
        self.filename = filename

    def __repr__(self):
        return f"DataFrameWrapper(id={self.id}, shape={self.dataframe.shape}, filename={self.filename})"


class DataProcessor:
    _instance = None
    _initialized = False  # Class-level attribute to track initialization

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DataProcessor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.data_store = {}  # Stores dataframes by ID
            self.file_store = {}  # Stores file paths by ID
            self.filename_store = {}  # Stores filenames by ID
            self._initialized = True  # Set the flag to True

    def process_file(self, file_content, filename):
        """
        Process uploaded file, load it into memory, and store it temporarily.
        Supports CSV, Excel, JSON, and Parquet files.

        Args:
            file_content (bytes): Content of the file.
            filename (str): Name of the file.

        Returns:
            DataFrameWrapper: A wrapper containing the loaded dataframe, its unique ID, and filename.

        Raises:
            ValueError: If the file format is unsupported or the file content is invalid.
        """
        logger.info(f"Processing file: {filename}")

        # Validate file name and content
        if not file_content:
            logger.error("File content is empty.")
            raise ValueError("File content is empty.")

        if not filename:
            logger.error("Filename is missing.")
            raise ValueError("Filename is missing.")

        # Temporarily store the file content
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        try:
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(file_content)
            logger.info(f"File stored temporarily at {temp_file_path}")

            # Detect file type and load data
            df = self._load_dataframe(temp_file_path)

            # Check for empty data or preprocess the dataframe
            df = self._check_and_preprocess_data(df)

        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            shutil.rmtree(temp_dir)  # Clean up temporary directory
            raise ValueError(f"Error processing file: {str(e)}")

        # Validate loaded dataframe
        if df.empty:
            logger.error("Loaded dataframe is empty.")
            shutil.rmtree(temp_dir)  # Clean up temporary directory
            raise ValueError("The uploaded file is empty.")

        logger.info(f"Successfully loaded data with shape {df.shape}")

        # Generate a unique ID and store the dataframe, file path, and filename
        data_id = str(uuid.uuid4())
        self.data_store[data_id] = df
        self.file_store[data_id] = temp_file_path
        self.filename_store[data_id] = filename
        logger.info(f"Data stored with ID: {data_id}, Filename: {filename}")

        return DataFrameWrapper(id=data_id, dataframe=df, filename=filename)

    def _load_dataframe(self, file_path):
        """
        Load a DataFrame from the given file path based on its extension.

        Args:
            file_path (str): Path to the file.

        Returns:
            pd.DataFrame: Loaded dataframe.
        """
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            logger.info("Detected CSV file.")
            return pd.read_csv(file_path)
        elif ext in [".xls", ".xlsx"]:
            logger.info("Detected Excel file.")
            return pd.read_excel(file_path)
        elif ext == ".json":
            logger.info("Detected JSON file.")
            return pd.read_json(file_path)
        elif ext == ".parquet":
            logger.info("Detected Parquet file.")
            return pd.read_parquet(file_path)
        else:
            logger.error("Unsupported file format.")
            raise ValueError(
                "Unsupported file format. Supported formats: CSV, Excel, JSON, Parquet."
            )

    # def _check_and_preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
    #     """
    #     Checks if the DataFrame has empty data and preprocesses it.
    #     Handles missing values, duplicates, converts categorical data to numerical,
    #     and attempts type corrections.

    #     Args:
    #         df (pd.DataFrame): The loaded dataframe.

    #     Returns:
    #         pd.DataFrame: The cleaned and preprocessed dataframe.
    #     """
    #     logger.info("Starting data preprocessing...")

    #     # Check if DataFrame is empty or contains only null values
    #     if df.empty or df.isnull().all().all():
    #         logger.warning("The DataFrame is empty or contains only null values.")
    #         return pd.DataFrame()  # Return an empty DataFrame

    #     # Drop rows where all values are NaN
    #     empty_rows = df.isnull().all(axis=1).sum()
    #     if empty_rows > 0:
    #         logger.info(f"Found {empty_rows} empty rows. Dropping them.")
    #         df = df.dropna(how="all")

    #     # Remove duplicate rows
    #     duplicate_rows = df.duplicated().sum()
    #     if duplicate_rows > 0:
    #         logger.info(f"Found {duplicate_rows} duplicate rows. Dropping them.")
    #         df = df.drop_duplicates()

    #     # Fill missing values based on column types
    #     for col in df.columns:
    #         if df[col].dtype in [float, int]:
    #             # Fill numeric columns with the mean
    #             df[col] = df[col].fillna(df[col].mean())
    #         elif df[col].dtype == object:
    #             # Fill categorical/text columns with a placeholder
    #             df[col] = df[col].fillna("Unknown")

    #     # Convert categorical columns to numerical using mapping
    #     for col in df.select_dtypes(include=["category", "object"]).columns:
    #         unique_values = df[col].dropna().unique()
    #         if len(unique_values) > 1:
    #             mapping = {val: idx for idx, val in enumerate(unique_values)}
    #             logger.info(f"Mapping for column '{col}': {mapping}")
    #             df[col] = df[col].map(mapping)

    #     # Convert date-like columns to datetime format
    #     for col in df.columns:
    #         if "date" in col.lower() or "time" in col.lower():
    #             try:
    #                 df[col] = pd.to_datetime(df[col], errors="coerce")
    #             except Exception as e:
    #                 logger.warning(f"Failed to convert column '{col}' to datetime: {str(e)}")

    #     # Drop columns with a single unique value (constant columns)
    #     constant_columns = [col for col in df.columns if df[col].nunique() <= 1]
    #     if constant_columns:
    #         logger.info(f"Dropping constant columns: {constant_columns}")
    #         df = df.drop(columns=constant_columns)

    #     # Scaling numerical columns if needed
    #     numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
    #     if not numeric_cols.empty:
    #         logger.info(f"Scaling numerical columns: {numeric_cols.tolist()}")
    #         df[numeric_cols] = (df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std()

    #     # Final info
    #     logger.info(f"Data after preprocessing: {df.shape[0]} rows and {df.shape[1]} columns.")
    #     return df

    def _check_and_preprocess_data(self, df):
        """
        Checks if the DataFrame has empty data and preprocesses it (removes nulls, duplicates, etc.).

        Args:
            df (pd.DataFrame): The loaded dataframe.

        Returns:
            pd.DataFrame: The cleaned and preprocessed dataframe.
        """
        # Check if DataFrame is empty
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

        # Handle missing values:
        # Forward fill for numeric columns and backward fill for object columns as an example
        for col in df.columns:
            if df[col].dtype in ["float64", "int64"]:
                # Fill missing numeric data with the column mean (or median for skewed distributions)
                df[col] = df[col].fillna(df[col].mean())  # Or use median() if needed
            else:
                # For categorical/string columns, forward fill (or use a placeholder for missing values)
                df[col] = df[col].fillna("Unknown")

        # Convert date columns to datetime (if applicable)
        for col in df.select_dtypes(include=[object]).columns:
            try:
                # Attempt to convert object columns to datetime
                df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
            except Exception as e:
                logger.info(
                    f"Column '{col}' could not be converted to datetime: {str(e)}"
                )

        # Handle other object types (convert categorical columns to 'category' dtype)
        for col in df.select_dtypes(include=[object]).columns:
            if df[col].dtype != "datetime64[ns]":
                df[col] = df[col].astype("category")

        # Ensure columns are appropriately typed:
        # Example: Enforce certain columns to be integers or floats if required
        for col in df.columns:
            if col in ["User_ID", "Product_ID"]:  # Example for IDs
                df[col] = df[col].astype("string")  # or 'object' if preferred
            elif df[col].dtype == "float64" or df[col].dtype == "int64":
                df[col] = df[col].astype(
                    "float64"
                )  # Ensure numeric columns are floats if needed

        logger.info(
            f"Data after preprocessing: {df.shape[0]} rows and {df.shape[1]} columns."
        )

        return df

    def get_data_by_id(self, data_id):
        """
        Retrieve dataframe by its unique ID.

        Args:
            data_id (str): Unique identifier for the dataframe.

        Returns:
            pd.DataFrame: The requested dataframe.

        Raises:
            ValueError: If the ID is invalid or data is not found.
        """
        logger.info(f"Fetching data with ID: {data_id}")
        if data_id not in self.data_store:
            logger.error(f"Data with ID {data_id} not found.")
            raise ValueError(f"Data with ID {data_id} not found.")
        return self.data_store[data_id]

    def get_file_path_by_id(self, data_id):
        """
        Retrieve file path by its unique ID.

        Args:
            data_id (str): Unique identifier for the file.

        Returns:
            str: Path to the file.

        Raises:
            ValueError: If the ID is invalid or file is not found.
        """
        logger.info(f"Fetching file path with ID: {data_id}")
        if data_id not in self.file_store:
            logger.error(f"File with ID {data_id} not found.")
            raise ValueError(f"File with ID {data_id} not found.")
        return self.file_store[data_id]

    def get_filename_by_id(self, data_id):
        """
        Retrieve filename by its unique ID.

        Args:
            data_id (str): Unique identifier for the file.

        Returns:
            str: Original filename.

        Raises:
            ValueError: If the ID is invalid or filename is not found.
        """
        logger.info(f"Fetching filename with ID: {data_id}")
        if data_id not in self.filename_store:
            logger.error(f"Filename with ID {data_id} not found.")
            raise ValueError(f"Filename with ID {data_id} not found.")
        return self.filename_store[data_id]

    def clean_up(self, data_id):
        """
        Clean up temporary file and dataframe associated with the given ID.

        Args:
            data_id (str): Unique identifier for the dataset.

        Raises:
            ValueError: If the ID is invalid.
        """
        logger.info(f"Cleaning up resources for ID: {data_id}")
        if data_id in self.file_store:
            temp_file_path = self.file_store.pop(data_id)
            temp_dir = os.path.dirname(temp_file_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Temporary file at {temp_file_path} deleted.")
        if data_id in self.data_store:
            self.data_store.pop(data_id)
            logger.info(f"DataFrame with ID {data_id} removed.")
        if data_id in self.filename_store:
            self.filename


# Instantiate a shared DataProcessor
data_processor = DataProcessor()
