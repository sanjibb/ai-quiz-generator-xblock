function AIQuizGeneratorXBlock(runtime, element, args) {
    const topicInput = $('#quiz-topic', element);
    const quizOutput = $('#quiz-output', element);
    const messageContainer = $('.message', element);
    const messageText = $('.message__title', element);
    const confirmButton = $('.btn-confirm', element);

    function showMessage(msg, type) {
        messageContainer.removeClass('message--hide bg-success bg-danger');
        messageContainer.addClass(type === 'error' ? 'bg-danger' : 'bg-success');
        messageText.text(msg);
    }

    function resetMessage() {
        messageContainer.removeClass('bg-success bg-danger').addClass('message--hide');
        messageText.text('');
    }

    function showGeneratedQuiz(result) {
        resetMessage();
        if (result.hasOwnProperty('error')) {
            showMessage(result.error, 'error');
            return;
        }
        quizOutput.text(result.generated_quiz);
        showMessage(gettext('Quiz generated successfully!'), 'success');
        confirmButton.removeClass('d-none');
    }

    function confirmQuizSuccess(result) {
        if (result.success) {
            showMessage(gettext('Quiz successfully added to unit!'), 'success');
        } else {
            showMessage(result.error || 'Error confirming quiz.', 'error');
        }
    }

    const generateQuizUrl = runtime.handlerUrl(element, 'generate_quiz');
    const confirmQuizUrl = runtime.handlerUrl(element, 'confirm_quiz');

    $('.btn-generate', element).click(function () {
        const topicText = topicInput.val().trim();
        const numQuestions = parseInt($('#num-questions', element).val());

        if (!topicText) {
            showMessage(gettext('Please enter a topic.'), 'error');
            return;
        }

        $.ajax({
            type: "POST",
            url: generateQuizUrl,
            data: JSON.stringify({ topic: topicText, num_quizzes: numQuestions }),
            success: showGeneratedQuiz
        });
    });

    $('.btn-confirm', element).click(function () {
        const quizText = quizOutput.text().trim();
        if (!quizText) {
            showMessage(gettext('No quiz to confirm.'), 'error');
            return;
        }

        $.ajax({
            type: "POST",
            url: confirmQuizUrl,
            data: JSON.stringify({ quiz: quizText }),
            success: confirmQuizSuccess
        });
    });
}

