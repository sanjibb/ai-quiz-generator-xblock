/* Javascript for AIQuizGeneratorXBlock */
function AIQuizGeneratorXBlock(runtime, element, args) {

    const topicInput = $('#quiz-topic', element);
    const quizOutput = $('#quiz-output', element);
    const messageContainer = $('.message', element);
    const messageText = $('.message__title', element);

    function showSuccessMessage(msg) {
        messageContainer.removeClass('message--hide bg-danger').addClass('bg-success');
        messageText.text(msg);
    }

    function showErrorMessage(msg) {
        messageContainer.removeClass('message--hide bg-success').addClass('bg-danger');
        messageText.text(msg);
    }

    function resetMessage() {
        messageContainer.removeClass('bg-success bg-danger').addClass('message--hide');
        messageText.text('');
    }

    function showGeneratedQuiz(result) {
        resetMessage();

        if (result.hasOwnProperty('error')) {
            showErrorMessage(result.error);
            return;
        }

        quizOutput.text(result.generated_quiz);
        showSuccessMessage(gettext('Quiz generated successfully!'));
    }

    const generateQuizUrl = runtime.handlerUrl(element, 'generate_quiz');

    $('.btn-generate', element).click(function () {
        const topicText = topicInput.val().trim();
        if (!topicText) {
            showErrorMessage(gettext('Please enter a topic before generating a quiz.'));
            return;
        }

        $.ajax({
            type: "POST",
            url: generateQuizUrl,
            data: JSON.stringify({ topic: topicText }),
            success: showGeneratedQuiz
        });
    });

    $(function ($) {
        // Optional: code to run when the DOM is ready
    });
}

