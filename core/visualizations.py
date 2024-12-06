import base64
import io
import logging
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configure the logging
logging.basicConfig(
    level=logging.INFO,  # Set the level to INFO or DEBUG to see more logs
    format="%(asctime)s [%(levelname)s] %(message)s",  # Add a timestamp and level to log messages
    handlers=[logging.StreamHandler()],  # Log to console
)
logger = logging.getLogger(__name__)


class VisualizationGenerator:

    def parse_query(self, query: str) -> tuple:
        """
        Parse the user query to determine the type of plot and target column(s).
        Returns a tuple of (plot_type, column(s)).
        """
        try:
            query = query.lower()

            # Define some basic mapping of query terms to plot types
            if "histogram" in query:
                plot_type = "histogram"
            elif "bar" in query:
                plot_type = "bar"
            elif "line" in query:
                plot_type = "line"
            elif "scatter" in query:
                plot_type = "scatter"
            elif "box" in query:
                plot_type = "box"
            elif "heatmap" in query:
                plot_type = "heatmap"
            elif "pairplot" in query:
                plot_type = "pairplot"
            elif "violin" in query:
                plot_type = "violin"
            else:
                plot_type = "unknown"

            # Try to extract columns dynamically
            columns = self.extract_columns(query)

            # Return plot type and columns found
            return plot_type, columns
        except Exception as e:
            logger.error(f"Error parsing query: {e}")
            return "unknown", []

    def extract_columns(self, query: str) -> list:
        """
        Extract column names from the user's query.
        Uses a mix of regex and NLP-like heuristics for better accuracy.
        """
        columns = []

        # Attempt to find column names mentioned after common patterns
        # Example: "for the 'age' column", "based on 'age'", "show me the data for 'age' and 'income'"
        column_patterns = [
            r"\b(\w+)\s*column\b",  # Example: age column
            r"column\s*['\"]?(\w+)['\"]?",  # Catch-all for any words (may need refinement)
        ]

        for pattern in column_patterns:
            matches = re.findall(pattern, query)
            columns.extend(matches)

        # Remove duplicates and return a clean list of column names
        return list(set(columns))

    def generate_plot(self, df: pd.DataFrame, query: str) -> str:
        """
        Generate a plot based on the user's query and return the plot as a base64 string.
        """
        logger.info("Parsing query for visualization.")
        plot_type, columns = self.parse_query(query)
        logger.info(f"plot type: {plot_type}, columns:{columns}")
        if plot_type == "unknown":
            return "Error: Could not determine the type of plot from the query."

        if not columns:
            columns = df.columns[:4].tolist()  # Select the first 4 columns
            logger.info(
                f"No columns specified. Defaulting to first 4 columns: {columns}"
            )

        if len(columns) > 1 and plot_type not in ["scatter", "pairplot"]:
            plot_type = "pairplot"

        # Normalize and check if the columns match the dataframe columns (case insensitive)
        normalized_columns = [col.lower() for col in columns]
        matched_columns = []

        for col in normalized_columns:
            # Try to match the column name case-insensitively
            matched_col = next(
                (df_col for df_col in df.columns if df_col.lower() == col), None
            )
            if matched_col:
                matched_columns.append(matched_col)
            else:
                logger.warning(
                    f"Column '{col}' could not be matched with any dataframe column."
                )

        # If no valid columns matched, return an error
        if not matched_columns:
            return f"Error: Could not match any of the specified columns '{', '.join(columns)}' to the dataframe."

        logger.info(f"Matched columns: {matched_columns}")

        plt.figure(figsize=(10, 6))  # Ensure consistent plot sizing
        try:
            # Handle different plot types
            if plot_type == "histogram":
                return self._generate_histogram(df, matched_columns[0])
            elif plot_type == "bar":
                return self._generate_bar_chart(df, matched_columns[0])
            elif plot_type == "line":
                return self._generate_line_plot(df, matched_columns[0])
            elif plot_type == "scatter":
                return self._generate_scatter_plot(df, matched_columns)
            elif plot_type == "box":
                return self._generate_box_plot(df, matched_columns[0])
            elif plot_type == "heatmap":
                return self._generate_heatmap(df, matched_columns)
            elif plot_type == "pairplot":
                return self._generate_pairplot(df, matched_columns)
            elif plot_type == "violin":
                return self._generate_violin_plot(df, matched_columns[0])
            else:
                return "Error: Unsupported plot type."

        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            return f"Error: Could not generate the plot. Details: {str(e)}"

    # Private method for histogram generation
    def _generate_histogram(self, df, column: str) -> str:
        logger.info(f"Generating histogram for column '{column}'")
        df[column].hist(bins=20, color="skyblue", edgecolor="black")
        plt.title(f"Histogram of {column}")
        plt.xlabel(column)
        plt.ylabel("Frequency")
        return self._save_plot_to_base64()

    # Private method for bar chart generation
    def _generate_bar_chart(self, df, column: str) -> str:
        logger.info(f"Generating bar chart for column '{column}'")
        df[column].value_counts().plot(
            kind="bar", color="lightgreen", edgecolor="black"
        )
        plt.title(f"Bar Chart of {column}")
        plt.xlabel(column)
        plt.ylabel("Count")
        return self._save_plot_to_base64()

    # Private method for line plot generation
    def _generate_line_plot(self, df, column: str) -> str:
        logger.info(f"Generating line plot for column '{column}'")
        df[column].plot(kind="line", marker="o", color="blue")
        plt.title(f"Line Plot of {column}")
        plt.xlabel("Index")
        plt.ylabel(column)
        return self._save_plot_to_base64()

    # Private method for scatter plot generation
    def _generate_scatter_plot(self, df, columns: list) -> str:
        if len(columns) == 2:
            x_col, y_col = columns
            logger.info(f"Generating scatter plot for columns '{x_col}' vs '{y_col}'")
            df.plot.scatter(x=x_col, y=y_col, color="purple")
            plt.title(f"Scatter Plot of {x_col} vs {y_col}")
            plt.xlabel(x_col)
            plt.ylabel(y_col)
            return self._save_plot_to_base64()
        else:
            logger.error("Scatter plot requires exactly two columns.")
            return "Error: Scatter plot requires exactly two columns."

    # Private method for box plot generation
    def _generate_box_plot(self, df, column: str) -> str:
        logger.info(f"Generating box plot for column '{column}'")
        sns.boxplot(x=df[column], color="lightcoral")
        plt.title(f"Box Plot of {column}")
        plt.xlabel(column)
        return self._save_plot_to_base64()

    # Private method for heatmap generation
    def _generate_heatmap(self, df, columns: list) -> str:
        logger.info("Generating heatmap for correlation matrix")
        corr_matrix = df.corr()
        sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", linewidths=0.5)
        plt.title("Heatmap of Feature Correlations")
        return self._save_plot_to_base64()

    # Private method for pairplot generation
    def _generate_pairplot(self, df, columns: list) -> str:
        logger.info(f"Generating pairplot for columns {columns}")
        sns.pairplot(df[columns])
        plt.title(f"Pairplot of {', '.join(columns)}")
        return self._save_plot_to_base64()

    # Private method for violin plot generation
    def _generate_violin_plot(self, df, column: str) -> str:
        logger.info(f"Generating violin plot for column '{column}'")
        sns.violinplot(x=df[column], color="seagreen")
        plt.title(f"Violin Plot of {column}")
        plt.xlabel(column)
        return self._save_plot_to_base64()

    # Helper method to save the plot to a base64 string
    def _save_plot_to_base64(self) -> str:
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"
