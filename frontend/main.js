// frontend/scripts/main.js
function fetchOdds() {
    const location = document.getElementById('location').value;
    const date = document.getElementById('date').value;
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = 'Загрузка...';

    const payload = {
        location: location,
        date: date
    };

    fetch('http://127.0.0.1:5000/api/weather-odds', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })
    .then(response => response.json())
    .then(data => {
        // Отображение тестового результата
        let html = `<h2>Вероятности:</h2>`;
        html += `<p>Жарко: ${data.probabilities.very_hot}</p>`;
        html += `<p>Влажно: ${data.probabilities.very_wet}</p>`;
        html += `<p>Некомфортно: ${data.probabilities.very_uncomfortable}</p>`;
        resultsDiv.innerHTML = html;

        // Здесь нужно будет добавить код для построения графиков (Chart.js или D3.js)
    })
    .catch(error => {
        resultsDiv.innerHTML = `<p style="color:red;">Ошибка связи с сервером: ${error}</p>`;
        console.error('Error:', error);
    });
}



