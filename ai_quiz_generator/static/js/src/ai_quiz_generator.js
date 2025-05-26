/* JavaScript for AIQuizGeneratorXBlock */

function AIQuizGeneratorXBlock(runtime, element, context) {
    const topicInput = $('#quiz-topic', element);
    const quizOutput = $('#quiz-output', element);
    const quizEditor = $('#quiz-editor', element);
    const submitButton = $('#submit-to-unit', element);
    const downloadButton = $('#download-tarball', element);
    const submissionStatus = $('#submission-status', element);
    const messageContainer = $('.message', element);
    const messageText = $('.message__title', element);

    // Utility: Show messages
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
        if (result.error) {
            showErrorMessage(result.error);
            return;
        }
        quizOutput.text(result.generated_quiz);
        quizEditor.val(result.generated_quiz);
        showSuccessMessage("Quiz generated successfully!");
    }

    const generateQuizUrl = runtime.handlerUrl(element, 'generate_quiz');
    const saveQuizUrl = runtime.handlerUrl(element, 'save_edited_quiz');

    $('.btn-generate', element).on('click', function () {
        const topicText = topicInput.val().trim();
        if (!topicText) {
            showErrorMessage("Please enter a prompt before generating a quiz.");
            return;
        }

        $.ajax({
            type: "POST",
            url: generateQuizUrl,
            data: JSON.stringify({ topic: topicText }),
            contentType: "application/json",
            success: showGeneratedQuiz,
            error: function () {
                showErrorMessage("Failed to generate quiz. Please try again.");
            }
        });
    });

    submitButton.on('click', function () {
        const editedText = quizEditor.val().trim();
        if (!editedText) {
            submissionStatus.text("⚠️ Edited quiz content is empty.");
            return;
        }

        $.ajax({
            type: "POST",
            url: saveQuizUrl,
            data: JSON.stringify({ edited_quiz: editedText }),
            contentType: "application/json",
            success: function (response) {
                if (response.success) {
                    submissionStatus.text("✅ Quiz saved successfully to the unit.");
                } else {
                    submissionStatus.text("❌ Error saving quiz: " + (response.error || 'Unknown error.'));
                }
            },
            error: function () {
                submissionStatus.text("❌ Failed to contact server.");
            }
        });
    });

    // ✅ FIXED: Download .tar.gz file using correct GET URL
    downloadButton.on('click', function () {
        const downloadUrl = runtime.handlerUrl(element, 'download_course_tar');
        console.log("📦 Downloading from:", downloadUrl);

        fetch(downloadUrl, {
            method: "GET",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(response => {
            if (!response.ok) throw new Error("Download failed");
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "ai_quiz_course.tar.gz";
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(error => {
            alert("Download failed: " + error.message);
        });
    });

    console.log("✅ AIQuizGeneratorXBlock initialized for:", element);
}
