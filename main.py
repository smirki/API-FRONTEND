
import openai

# Initialize the OpenAI API with your token
openai.api_key = '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'

def generate_open_ended_question(content, previous_answers):
    prompt = f"Create an open-ended question based on the following information: {content}"
    
    # Add context from previous answers if available
    if previous_answers:
        incorrect_answers = [ans for ans in previous_answers if not ans['is_correct']]
        if incorrect_answers:
            prompt += f" The student had difficulty with: {incorrect_answers[-1]['question']}"
    
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=100
    )
    
    return response.choices[0].text.strip()

def check_answer(question, answer):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"Is the following answer correct for the question? Question: {question}. Answer: {answer}. Just reply with yes or no.",
        max_tokens=10
    )
    
    response_text = response.choices[0].text.strip().lower()
    return 'yes' if 'yes' in response_text else 'no'


def generate_report(all_answers):
    incorrect_questions = [ans['question'] for ans in all_answers if not ans['is_correct']]
    summary = f"The student had difficulty with the following questions: {'; '.join(incorrect_questions)}."

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"Provide a detailed report based on the student's performance. {summary}",
        max_tokens=200
    )
    
    return response.choices[0].text.strip()

# Input the content
content = input("Enter the content for the quiz: ")
num_questions = int(input("Enter the number of questions you want to generate: "))

student_data = []

for _ in range(num_questions):
    question = generate_open_ended_question(content, student_data)
    answer = input(f"\nQuestion: {question}\nEnter your answer: ")
    
    is_correct = check_answer(question, answer)
    
    student_data.append({'question': question, 'answer': answer, 'is_correct': is_correct})

# Generate a report based on all answers
report = generate_report(student_data)
print("\nReport:")
print(report)