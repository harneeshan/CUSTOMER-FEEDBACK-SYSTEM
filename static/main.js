document.addEventListener('DOMContentLoaded', () => {
    loadFeedback();

    const form = document.getElementById('feedbackForm');
    if (form) {
        const starLabels = document.querySelectorAll('.star-label');
        const starInputs = document.querySelectorAll('input[name="rating"]');

        // Function to update star highlighting
        function updateStars(selectedIndex) {
            starLabels.forEach((label, index) => {
                if (index <= selectedIndex) {
                    label.classList.add('star-filled');
                } else {
                    label.classList.remove('star-filled');
                }
            });
        }

        // Handle star clicks
        starInputs.forEach((input, index) => {
            input.addEventListener('change', () => {
                updateStars(index);
            });
        });

        // Handle hover effects
        starLabels.forEach((label, index) => {
            label.addEventListener('mouseover', () => {
                updateStars(index);
            });
            label.addEventListener('mouseout', () => {
                const checkedIndex = Array.from(starInputs).findIndex(input => input.checked);
                updateStars(checkedIndex);
            });
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form_id = document.getElementById('form_id').value;
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const feedback = document.getElementById('feedback').value;
            const rating = parseInt(document.querySelector('input[name="rating"]:checked').value);

            try {
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ form_id, name, email, feedback, rating })
                });
                if (response.ok) {
                    form.reset();
                    updateStars(-1); // Reset stars after submission
                    loadFeedback();
                    alert('Feedback submitted successfully!');
                } else {
                    const error = await response.json();
                    alert(error.error || 'Error submitting feedback.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred.');
            }
        });
    }
});

async function loadFeedback() {
    try {
        const response = await fetch('/api/feedback');
        const feedbackList = await response.json();
        const tableBody = document.getElementById('feedbackTableBody');
        tableBody.innerHTML = '';

        feedbackList.forEach(item => {
            const row = document.createElement('tr');
            const isAdmin = document.querySelector('body').dataset.role === 'admin';
            row.innerHTML = `
                <td>${item.form_title}</td>
                <td>${item.name}</td>
                <td>${item.email}</td>
                <td>${item.feedback}</td>
                <td>
                    <span class="star-rating" style="--rating-width: ${item.rating * 20}%"></span>
                </td>
                <td>${item.created_at}</td>
                ${isAdmin ? `<td><button onclick="deleteFeedback(${item.id})" class="delete-button">Delete</button></td>` : ''}
            `;
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading feedback:', error);
    }
}

async function deleteFeedback(id) {
    if (confirm('Are you sure you want to delete this feedback?')) {
        try {
            const response = await fetch(`/api/feedback/${id}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                loadFeedback();
                alert('Feedback deleted successfully!');
            } else {
                alert('Error deleting feedback.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred.');
        }
    }
}