from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import jsonify
import openai
from flask_socketio import SocketIO, emit



app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = 'some_secret_key'  # A secret key for Flask's session

# Initialize the OpenAI API with your token
openai.api_key = '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'


# Global variables to store quiz state and data
quiz_data = {
    'content': '',
    'num_questions': 0,
    'active': False,
    'students': {},  # Store student data by ID
    'custom_questions': []  # Initialize custom questions
}


@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    global quiz_data
    if request.method == 'POST':
        # Capture custom questions and their answers if provided
        print("Form data received:", request.form)  # Diagnostic print
        custom_questions = request.form.getlist('custom_question[]')
        custom_answers = request.form.getlist('custom_answer[]')
        quiz_data['content'] = request.form.get('content', '')
        quiz_data['num_questions'] = int(request.form.get('num_questions', 0))
        quiz_data['custom_questions'] = list(zip(custom_questions, custom_answers))
        
        # Determine if we're on the Custom Questions tab or the Smart Questions tab
        tab_type = request.form.get('tab_type', 'smart')  # Default to "smart" if not provided
        
        if tab_type == 'smart' and not quiz_data['content']:
            flash("Please provide content for smart questions before starting the quiz.", "error")
            return render_template('teacher.html', quiz_data=quiz_data)
        if tab_type == 'custom' and not quiz_data['custom_questions']:
            flash("Please provide custom questions before starting the quiz.", "error")
            return render_template('teacher.html', quiz_data=quiz_data)
        
        
        
        if 'start' in request.form:
            quiz_data['active'] = True
            flash("Quiz started successfully!", "success")
            # Check if there are custom questions. If yes, don't rely on OpenAI
            if custom_questions:
                quiz_data['use_openai'] = False
            else:
                quiz_data['use_openai'] = True
            
        if 'end' in request.form:
            quiz_data = {
                'content': '',
                'num_questions': 0,
                'active': False,
                'students': {},  # Store student data by ID
                'custom_questions': []  # Initialize custom questions
            }
            flash("Quiz ended and data reset successfully!", "success")


        elif 'collect' in request.form:
            # For simplicity, just print reports to the console
            for student_id, answers in quiz_data['students'].items():
                report = generate_report(answers)
                print(f"Report for Student {student_id}: {report}")
            return redirect(url_for('teacher'))
    return render_template('teacher.html', quiz_data=quiz_data)

@app.route('/student/<id>', methods=['GET', 'POST'])
def student(id):
    if not quiz_data['active']:
        return "Quiz not active. Please wait for the teacher to start the quiz."
    
    if id not in quiz_data['students']:
        quiz_data['students'][id] = []
    
    if request.method == 'POST':
        answer = request.form['answer']
        question = request.form['question']
        print(answer)

        socketio.emit('student_update', {'student_id': id, 'results': quiz_data['students'][id]})
        
        if quiz_data['use_openai']:
            is_correct = check_answer(question, answer)
        else:
            # Check if the answer matches the custom answer
            is_correct = any((q == question and a == answer) for q, a in quiz_data['custom_questions'])
        
        quiz_data['students'][id].append({'question': question, 'answer': answer, 'is_correct': is_correct})
        
        if len(quiz_data['students'][id]) < quiz_data['num_questions']:
            return redirect(url_for('student', id=id))
        else:
            return "Quiz completed. Thank you!"
    
    if quiz_data['use_openai']:
        if not quiz_data['content']:
            return "No content available for generating questions. Please contact the teacher."

        question = generate_open_ended_question(quiz_data['content'], quiz_data['students'][id])
    else:
        # Use one of the custom questions
        used_questions = [ans['question'] for ans in quiz_data['students'][id]]
        available_questions = [q for q, _ in quiz_data['custom_questions'] if q not in used_questions]
        question = available_questions[0] if available_questions else "No more questions available."
        if not available_questions:
            return "No more questions available. Please contact the teacher."
    return render_template('student.html', question=question)

# ... [Rest of the functions remain unchanged]


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
        prompt=f"Is the following answer correct for the question? Question: {question}. Answer: {answer}. Answer with yes or no.",
        max_tokens=10
    )

    print("HI", response.choices[0].text)
    
    response_text = response.choices[0].text.strip().lower()
    return 'yes' in response_text


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'student_data' not in session:
        session['student_data'] = []
    
    if request.method == 'GET':
        question = generate_open_ended_question(content, session['student_data'])
        return render_template('quiz.html', question=question)
    else:  # POST request
        answer = request.form['answer']
        question = request.form['question']
        
        is_correct = check_answer(question, answer)
        
        session['student_data'].append({'question': question, 'answer': answer, 'is_correct': is_correct})
        
        if len(session['student_data']) < num_questions:
            return redirect(url_for('index'))
        else:
            report = generate_report(session['student_data'])
            session.clear()  # Clear the session data
            return render_template('report.html', report=report)

def generate_report(all_answers):
    incorrect_questions = [ans['question'] for ans in all_answers if not ans['is_correct']]
    summary = f"The student had difficulty with the following questions: {'; '.join(incorrect_questions)}."

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"Provide a detailed report based on the student's performance. {summary}",
        max_tokens=200
    )
    
    return response.choices[0].text.strip()

@app.route('/quiz_data', methods=['GET'])
def get_quiz_data():
    data = {
        "students": [],
        "num_questions": quiz_data['num_questions']
    }
    for student_id, answers in quiz_data['students'].items():
        correct_by_question = [ans['is_correct'] for ans in answers]
        data["students"].append({"student_id": student_id, "results": correct_by_question})
    return jsonify(data)

@app.route('/student/<id>/report', methods=['GET'])
def student_report(id):
    if id in quiz_data['students']:
        report = generate_report(quiz_data['students'][id])
        return report
    return "No report available for this student."



if __name__ == '__main__':
    app.run(debug=True)
