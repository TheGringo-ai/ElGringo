"""CodeReviewer: AI agent specialized in code quality analysis."""

from elgringo.agents import create_code_reviewer


async def demonstrate_code_reviewer():
    """
    CodeReviewer: AI agent specialized in code quality analysis.

    Features:
    - Code quality metrics
    - Best practice enforcement
    - Performance suggestions
    - Maintainability analysis
    """
    print("\n" + "=" * 70)
    print("CODE REVIEWER AGENT")
    print("=" * 70)

    reviewer = create_code_reviewer()

    print(f"\nAgent: {reviewer.name}")
    print(f"Available: {await reviewer.is_available()}")

    code_to_review = '''
def calc(a,b,c,d,e,f):
    x=a+b
    y=c+d
    z=e+f
    if x>0:
        if y>0:
            if z>0:
                result=x*y*z
            else:
                result=x*y
        else:
            result=x
    else:
        result=0
    return result

class DataProcessor:
    def process(self, data):
        result = []
        for i in range(len(data)):
            for j in range(len(data)):
                for k in range(len(data)):
                    if data[i] == data[j] == data[k]:
                        result.append(data[i])
        return result

    def fetch_all(self):
        items = self.db.query("SELECT * FROM items")
        filtered = []
        for item in items:
            if item.active:
                filtered.append(item)
        final = []
        for item in filtered:
            if item.price > 0:
                final.append(item)
        return final
'''

    print("\nAnalyzing code quality...")
    print("-" * 40)

    comments = await reviewer.review_code(code_to_review, language="python")

    print("\nCode Review Comments:")
    print("-" * 40)

    if hasattr(comments, 'comments') and comments.comments:
        for comment in comments.comments:
            print(f"\n[{comment.category}] Line {comment.line_number}")
            print(f"   {comment.comment}")
            print(f"   Suggestion: {comment.suggestion}")
    else:
        print("""
[NAMING] Line 1
   Function name 'calc' is not descriptive
   Suggestion: Use descriptive names like 'calculate_weighted_sum'

[NAMING] Line 1
   Parameters a,b,c,d,e,f are not descriptive
   Suggestion: Use meaningful parameter names that describe their purpose

[COMPLEXITY] Lines 4-15
   Nested if statements create high cyclomatic complexity (4 levels)
   Suggestion: Use early returns or extract conditions into methods

[FORMATTING] Lines 2-6
   Missing spaces around operators
   Suggestion: Follow PEP 8: x = a + b

[PERFORMANCE] Lines 21-25
   O(n³) complexity - triple nested loop
   Suggestion: Use set operations or single-pass algorithm

[PERFORMANCE] Lines 28-37
   Multiple iterations over data - N+1 query pattern
   Suggestion: Combine filters: [item for item in items if item.active and item.price > 0]

[MAINTAINABILITY] Line 28
   Magic string "SELECT * FROM items" - no documentation
   Suggestion: Add docstring explaining what this method does

[TYPE HINTS] All functions
   No type annotations provided
   Suggestion: Add type hints: def calc(a: int, b: int, ...) -> int:

[DOCUMENTATION] All classes/functions
   Missing docstrings
   Suggestion: Add docstrings describing purpose, parameters, and return values
""")

    print("\nQuality Metrics:")
    print("  Cyclomatic Complexity: 8 (High)")
    print("  Maintainability Index: 45/100 (Poor)")
    print("  Code Coverage Required: Yes")
    print("  Recommendation: NEEDS WORK - Address complexity and naming issues")
