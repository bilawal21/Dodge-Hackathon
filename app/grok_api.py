import os
from openai import OpenAI
import re
from dotenv import load_dotenv

load_dotenv()

# Initialize Grok client
XAI_API_KEY = os.getenv("XAI_API_KEY")

class GrokAPI:
    def __init__(self):
        self.client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1",
        )

    def validate_and_fill_form(self, form_data):
        """
        Sends form data to Grok for validation and auto-fill.
        Handles non-JSON responses by extracting key-value pairs from unstructured text.
        :param form_data: Dictionary containing form fields (name, email, etc.)
        :return: Dictionary with missing or invalid form fields or error message
        """
        try:
            # Identify missing fields (fields with empty values)
            missing_fields = [key for key, value in form_data.items() if not value]
            
            # Identify invalid fields (fields that have incorrect values based on their formats)
            invalid_fields = self._check_for_invalid_formats(form_data)

            # Return early if no missing or invalid fields
            if not missing_fields and not invalid_fields:
                return {"message": "All fields are valid and complete."}

            # Prepare user message only for missing and invalid fields
            user_message = (
                f"Here is the tax form data: {form_data}. "
                f"Identify missing fields and their values or suggest corrections for invalid fields. "
                f"Missing fields: {missing_fields}, Invalid fields: {invalid_fields}."
            )

            # Get the response from Grok
            completion = self.client.chat.completions.create(
                model="grok-beta",
                messages=[ 
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant specialized in validating and auto-filling forms. "
                            "Provide corrected and completed form data in clear text with key-value pairs. "
                            "Example: 'Name: John Doe, Email: johndoe@example.com, Age: 30'."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
            )

            # Get the raw response text from Grok's completion
            raw_response = completion.choices[0].message.content

            # If Grok's response is just a success message (with no corrections), return the form data
            if "All fields are valid and complete" in raw_response:
                return form_data

            # Parse the response into a dictionary with field values
            filled_form = self._parse_response_to_dict(raw_response, form_data, missing_fields, invalid_fields)

            # Filter out only the missing or invalid fields to return
            result = {}
            for field in missing_fields + invalid_fields:
                result[field] = filled_form.get(field, "No value provided")

            return result

        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}

    def _check_for_invalid_formats(self, form_data):
        """
        Checks the form data for any invalid formats (e.g., email, phone number, postal code).
        :param form_data: Dictionary containing form fields (name, email, etc.)
        :return: List of fields with invalid formats.
        """
        invalid_fields = []

        # Full Name: Must only contain alphabets and spaces
        if 'full_name' in form_data:
            name_pattern = r"^[A-Za-z\s]+$"  # Validate full name (letters and spaces only)
            if not re.match(name_pattern, form_data['full_name']):
                invalid_fields.append('full_name')

        # Phone Number: Validate US phone number format (e.g., 123-456-7890)
        if 'phone_number' in form_data:
            phone_pattern = r"^\d{3}-\d{3}-\d{4}$"
            if not re.match(phone_pattern, form_data['phone_number']):
                invalid_fields.append('phone_number')

        # Email: Validate email format (e.g., test@example.com)
        if 'email' in form_data:
            email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_pattern, form_data['email']):
                invalid_fields.append('email')

        # Postal Code: Validate US postal code (e.g., 12345 or 12345-6789)
        if 'postal_code' in form_data:
            postal_code_pattern = r"^\d{5}(-\d{4})?$"
            if not re.match(postal_code_pattern, form_data['postal_code']):
                invalid_fields.append('postal_code')

        # Street Address: Ensure it's not empty and valid format
        if 'street_address' in form_data:
            if not form_data['street_address'] or not re.match(r"^[A-Za-z0-9\s,.-]+$", form_data['street_address']):
                invalid_fields.append('street_address')

        # City: Only alphabetic characters and spaces
        if 'city' in form_data:
            city_pattern = r"^[A-Za-z\s]+$"
            if not re.match(city_pattern, form_data['city']):
                invalid_fields.append('city')

        # State: Only alphabetic characters and spaces
        if 'state' in form_data:
            state_pattern = r"^[A-Za-z\s]+$"
            if not re.match(state_pattern, form_data['state']):
                invalid_fields.append('state')

        # Country: Check if it's a valid country name (for simplicity, we can allow alphabetic characters and spaces)
        if 'country' in form_data:
            country_pattern = r"^[A-Za-z\s]+$"
            if not re.match(country_pattern, form_data['country']):
                invalid_fields.append('country')

        return invalid_fields

    def _parse_response_to_dict(self, response_text, original_form, missing_fields, invalid_fields):
        """
        Parses unstructured text response and maps it to the original form fields.
        :param response_text: Unstructured text from the model's response.
        :param original_form: Original form data as a dictionary.
        :param missing_fields: List of fields that are missing.
        :param invalid_fields: List of fields with invalid formats.
        :return: Dictionary with extracted field values.
        """
        # Use a regex to extract key-value pairs from the response
        extracted_data = {}

        # Sanitize the response by removing unwanted characters like asterisks or extra spaces
        sanitized_response = self._sanitize_response(response_text)

        for field in original_form.keys():
            # Search for patterns like "Field Name: Value" in the response
            match = re.search(rf"{field}[:=]\s*(.+)", sanitized_response, re.IGNORECASE)
            if match:
                extracted_data[field] = match.group(1).strip()
            else:
                # If no value is found, keep the original value (or leave empty if missing)
                extracted_data[field] = original_form.get(field, "")

            # Handle missing fields - explicitly mark them
            if not extracted_data[field] and field in missing_fields:
                extracted_data[field] = f"Missing {field}"

            # Handle invalid formats - explicitly mark them
            if field in invalid_fields and not extracted_data[field]:
                extracted_data[field] = f"Invalid {field} format"

        return extracted_data

    def _sanitize_response(self, response_text):
        """
        Sanitizes the response text by removing unwanted characters such as asterisks or extra spaces.
        :param response_text: The raw response text from the model.
        :return: Sanitized response text.
        """
        # Remove unwanted asterisks and leading/trailing spaces
        sanitized_text = re.sub(r"\*\*", "", response_text)  # Remove asterisks
        sanitized_text = sanitized_text.strip()  # Remove leading/trailing spaces
        return sanitized_text
