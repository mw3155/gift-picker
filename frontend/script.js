document.addEventListener("DOMContentLoaded", () => {
  const currentPath = window.location.pathname.split("/").pop();

  if (!currentPath || currentPath === "index.html") {
    const generateButton = document.getElementById("generate-link");
    const linkOutput = document.getElementById("link-output");

    generateButton.addEventListener("click", async () => {
      try {
        const response = await fetch("http://localhost:8000/generate-chat-link", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });
        const data = await response.json();
        linkOutput.textContent = `Share this link: ${data.link_a}`;
      } catch (error) {
        linkOutput.textContent = "Failed to generate link. Please try again.";
      }
    });
  }

  if (currentPath === "chat.html") {
    const questions = [
      "What is your favorite hobby?",
      "What is something you’ve always wanted?",
      "Do you prefer practical or sentimental gifts?",
    ];
    let currentQuestion = 0;
    let responses = [];
    const questionEl = document.getElementById("question");
    const answerEl = document.getElementById("answer");
    const nextButton = document.getElementById("next-question");
    const chatBox = document.getElementById("chat-box");
    const resultLinkEl = document.getElementById("result-link");

    questionEl.textContent = questions[currentQuestion];

    nextButton.addEventListener("click", async () => {
      const answer = answerEl.value.trim();
      if (!answer) {
        alert("Please enter an answer!");
        return;
      }
      responses.push(answer);
      answerEl.value = "";
      currentQuestion++;
      if (currentQuestion < questions.length) {
        questionEl.textContent = questions[currentQuestion];
      } else {
        const link_a = "example-chat-link-id"; // Replace with logic to fetch from URL
        try {
          const response = await fetch(`http://localhost:8000/complete-chat/${link_a}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ responses }),
          });
          const data = await response.json();
          resultLinkEl.textContent = `Share this link with User1: ${data.link_b}`;
          chatBox.style.display = "none";
        } catch (error) {
          alert("Failed to submit responses.");
        }
      }
    });
  }

  if (currentPath === "result.html") {
    const link_b = "example-result-link-id"; // Replace with logic to fetch from URL
    fetch(`http://localhost:8000/get-suggestions/${link_b}`)
      .then((response) => response.json())
      .then((data) => {
        const suggestionsEl = document.getElementById("suggestions");
        if (data.error) {
          suggestionsEl.textContent = "Failed to retrieve suggestions.";
        } else {
          data.gift_suggestions.forEach((suggestion) => {
            const li = document.createElement("li");
            li.textContent = suggestion;
            suggestionsEl.appendChild(li);
          });
        }
      })
      .catch(() => {
        alert("Failed to load suggestions.");
      });
  }
});
