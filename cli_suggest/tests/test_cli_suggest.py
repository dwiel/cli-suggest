import unittest
from cli_suggest.cli_suggest import extract_code_from_backticks

class TestExtractCodeFromBackticks(unittest.TestCase):
    def test_extract_code_with_backticks(self):
        input_text = """Here's some code:
```
def hello():
    print("Hello, world!")
```
And some more text."""
        expected_output = """def hello():
    print("Hello, world!")"""
        self.assertEqual(extract_code_from_backticks(input_text), expected_output)

    def test_extract_code_with_language_specified(self):
        input_text = """Here's some Python code:
```python
def greet(name):
    return f"Hello, {name}!"
```
End of code."""
        expected_output = """def greet(name):
    return f"Hello, {name}!"""
        self.assertEqual(extract_code_from_backticks(input_text), expected_output)

    def test_no_backticks(self):
        input_text = "This is just plain text without any code blocks."
        self.assertEqual(extract_code_from_backticks(input_text), input_text)

    def test_multiple_code_blocks(self):
        input_text = """First block:
```
print("First")
```
Second block:
```
print("Second")
```"""
        expected_output = """print("First")"""
        self.assertEqual(extract_code_from_backticks(input_text), expected_output)

    def test_empty_code_block(self):
        input_text = "Empty code block:\n```\n```\nEnd"
        expected_output = ""
        self.assertEqual(extract_code_from_backticks(input_text), expected_output)

if __name__ == '__main__':
    unittest.main()
