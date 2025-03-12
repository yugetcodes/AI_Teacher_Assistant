from flask import Flask, request, jsonify
import os
import re
import google.generativeai as generative_ai
from sympy import sympify, simplify, Eq, symbols, solve, diff, integrate, Derivative, Integral,sin, cos, tan, log, exp, Matrix, limit, series, Symbol
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Configure AI Model
generative_ai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
TEXT_MODEL = "gemini-2.0-flash-exp"

system_prompt = """
You are an AI teacher assistant evaluating student assignments.
Your feedback should:
- Be subject-specific (math, science, literature, programming).
- Identify grammar errors, logic flaws, miscalculations, conceptual misunderstandings.
- Adapt to the student’s proficiency level (beginner, intermediate, advanced).
- Detect plagiarism and encourage originality.
- Suggest additional resources for improvement.
- Highlight strengths as well as areas for improvement.

### Subject-Specific Guidelines:
1. **Math**: Solve the problem, compare it with the student’s answer, and give feedback.
2. **Programming**: Execute code (if safe), analyze output, suggest improvements.
"""

@app.route('/')
def home():
    return jsonify({"message": "Assignment evaluation API is running!"})

@app.route('/evaluate_assignment', methods=['POST'])
def evaluate_assignment():
    try:
        data = request.get_json()
        student_response = data.get("response", "")
        assignment_type = data.get("assignment_type", "general")
        proficiency_level = data.get("proficiency_level", "intermediate")

        if not student_response:
            return jsonify({"error": "Student response is required"}), 400

        if assignment_type == "math":
            return evaluate_math(student_response)
        elif assignment_type == "coding":
            return evaluate_code(student_response)
        else:
            return evaluate_general(student_response, assignment_type, proficiency_level)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred'}), 500

def evaluate_math(expression):
    try:
        x = symbols("x")  # Define 'x' as a symbolic variable

        # Preprocess the input to extract the mathematical expression
        # Example: "Find the derivative of 2x^2 + 3x" -> "2x^2 + 3x"
        math_expr_match = re.search(r'([\d\.]*[xX](\^\d+)?\s*[\+\-]?\s*[\d\.]*[xX]?(\^\d+)?)', expression)
        if not math_expr_match:
            return jsonify({"error": "No valid mathematical expression found in the input."}), 400

        math_expr = math_expr_match.group(0)
        math_expr = re.sub(r'(\d+)([xX])', r'\1*\2', math_expr)  # Insert '*' for multiplication
        math_expr = math_expr.replace('^', '**')  # Replace '^' with '**' for exponentiation

        # Check if the input contains an equation (`=`)
        if "=" in math_expr:
            lhs, rhs = math_expr.split("=")
            lhs_sympy = sympify(lhs.strip(), locals={"x": x})
            rhs_sympy = sympify(rhs.strip(), locals={"x": x})

            # Check if both sides are equal
            is_equal = simplify(lhs_sympy - rhs_sympy) == 0

            if is_equal:
                feedback = "Your equation is correct! Well done. 🎉"
            else:
                feedback = f"""
                Your equation simplifies to: {lhs_sympy} = {rhs_sympy}.
                The equation is incorrect. Here's why:
                - The left-hand side (LHS) simplifies to: {lhs_sympy}
                - The right-hand side (RHS) simplifies to: {rhs_sympy}
                - The difference between LHS and RHS is: {simplify(lhs_sympy - rhs_sympy)}
                Check your calculations and ensure both sides are balanced.
                """
            return jsonify({"feedback": feedback}), 200

        # If no `=`, check if it's a derivative, integral, or simplification problem
        if "derivative" in expression.lower() or "diff" in expression.lower():
            # Handle derivative problems
            expr = sympify(math_expr, locals={"x": x})
            derivative = diff(expr, x)
            feedback = f"""
            The derivative of your expression is: {derivative}.
            Ensure you applied the differentiation rules correctly.
            """
            return jsonify({"feedback": feedback}), 200

        elif "integral" in expression.lower() or "int" in expression.lower():
            # Handle integral problems
            expr = sympify(math_expr, locals={"x": x})
            integral = integrate(expr, x)
            feedback = f"""
            The integral of your expression is: {integral}.
            Double-check your integration steps.
            """
            return jsonify({"feedback": feedback}), 200

        else:
            # Handle simplification problems
            student_expr = sympify(math_expr, locals={"x": x})
            simplified_expr = simplify(student_expr)
            feedback = f"""
            Your answer simplifies to: {simplified_expr}.
            Ensure your calculations follow correct algebraic steps.
            """
            return jsonify({"feedback": feedback}), 200

    except Exception as e:
        return jsonify({"error": f"Invalid math expression: {e}"}), 400
def evaluate_code(code):
    try:
        if "import os" in code or "import sys" in code:  # Prevent dangerous imports
            return jsonify({"error": "Unsafe code detected"}), 400

        safe_globals = {"__builtins__": {}}  # Restrict built-in functions
        exec_globals = {}
        exec(code, safe_globals, exec_globals)
        return jsonify({
            "feedback": "Code executed successfully.",
            "output": exec_globals
        }), 200
    except Exception as e:
        return jsonify({"error": f"Code execution failed: {e}"}), 400

def evaluate_general(response, assignment_type, proficiency_level):
    prompt = f"""
    {system_prompt}
    Assignment Type: {assignment_type}
    Student Proficiency Level: {proficiency_level}

    Student Response:
    {response}

    Provide constructive feedback.
    """
    model = generative_ai.GenerativeModel(TEXT_MODEL)
    
    try:
        ai_response = model.generate_content(prompt)
        feedback = ai_response.text if hasattr(ai_response, "text") else "Error: No feedback generated."
        return jsonify({"feedback": feedback}), 200
    except Exception as e:
        return jsonify({"error": f"AI response error: {e}"}), 500

if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0', debug=True)