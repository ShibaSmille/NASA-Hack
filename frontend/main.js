const API_URL = 'http://127.0.0.1:5000/api/weather-odds';

// ----------------------------------------------------------------------
// НОВА ФУНКЦІЯ: Завантажує дані як JSON-файл
// ----------------------------------------------------------------------
function downloadJson(data, location, date) {
    // Формуємо ім'я файлу на основі міста та дати
    const filename = `NASA_Risk_Data_${location}_${date}.json`;
    
    // Перетворюємо об'єкт JavaScript в JSON-рядок з гарним форматуванням
    const jsonStr = JSON.stringify(data, null, 4);

    // Створюємо Blob (бінарний об'єкт) для файлу
    const blob = new Blob([jsonStr], { type: 'application/json' });
    
    // Створюємо тимчасове посилання для завантаження
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    
    // Імітуємо клік для початку завантаження
    document.body.appendChild(a);
    a.click();
    
    // Прибираємо тимчасове посилання
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log(`Файл ${filename} успішно згенеровано та завантажено.`);
}
// ----------------------------------------------------------------------

function createBarChart(probabilities) {
    if (!probabilities) return '';
    
    // Перетворення об'єкта ймовірностей на масив для ітерації
    const riskData = [
        { name: 'Пляж (T<24/Rain>5)', value: parseInt(probabilities.very_hot), color: 'bg-blue-600' },
        { name: 'Лижі (T>0)', value: parseInt(probabilities.very_wet), color: 'bg-gray-600' },
        { name: 'Туризм (T>30/Rain>10)', value: parseInt(probabilities.hiking_prob), color: 'bg-green-600' },
        { name: 'Риболовля (Rain>10/Wind>10)', value: parseInt(probabilities.fishing_prob), color: 'bg-red-600' },
        { name: 'Фестиваль (Rain>5/T>32)', value: parseInt(probabilities.very_uncomfortable), color: 'bg-yellow-600' }
    ];

    let barsHtml = riskData.map(item => `
        <div class="flex items-center space-x-2 py-1">
            <div class="w-1/3 text-sm font-medium text-gray-700">${item.name}</div>
            <div class="w-2/3 bg-gray-200 rounded-full h-6">
                <div class="h-6 rounded-full ${item.color} transition-all duration-700 ease-out" 
                     style="width: ${item.value}%; min-width: 10px;">
                    <span class="text-xs font-bold text-white pl-2 leading-6">${item.value}%</span>
                </div>
            </div>
        </div>
    `).join('');

    return `
        <div class="bg-white p-6 rounded-xl shadow-2xl mt-8">
            <h2 class="text-2xl font-extrabold text-indigo-700 mb-6">Візуалізація Історичного Ризику</h2>
            <div class="space-y-2">
                ${barsHtml}
            </div>
        </div>
    `;
}
// ----------------------------------------------------------------------

function createDataTable(data) {
    if (!data || data.length === 0) return '';

    let html = `
        <h3 class="text-xl font-bold mt-6 mb-3 text-indigo-700">Приклад історичних даних (Імітація Data Rods)</h3>
        <p class="text-sm mb-4 text-gray-600">Наш аналіз ґрунтується на 40 роках імітованих даних NASA. Ось 10 прикладів:</p>
        <div class="overflow-x-auto bg-gray-50 p-3 rounded-lg shadow-inner">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-200">
                    <tr>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Рік</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Темп. (C)</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Опади (мм)</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Вол. (%)</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Вітер (м/с)</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
    `;

    data.forEach((row, index) => {
        // Ми імітуємо 40 років, але показуємо лише 10, починаючи з 1984 року
        const year = 1984 + index; 
        html += `
            <tr>
                <td class="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">${year}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm">${row.Temp_C}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm">${row.Rain_mm}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm">${row.Humidity_RH}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm">${row.Wind_m_s}</td>
            </tr>
        `;
    });

    html += `</tbody></table></div>`;
    return html;
}

function fetchOdds() {
    console.log('--- Запуск fetchOdds() ---'); 
    
    const location = document.getElementById('location').value;
    const date = document.getElementById('date').value;
    const resultsDiv = document.getElementById('results');
    
    if (!location || !date) {
        resultsDiv.innerHTML = `
            <p class="text-red-600 font-bold p-4 bg-red-100 rounded-lg shadow-lg">
                ПОМИЛКА: Будь ласка, введіть місто та повну дату (РРРР-ММ-ДД).
            </p>`;
        return;
    }

    resultsDiv.innerHTML = '<div class="text-center py-4 text-lg text-gray-600">Завантаження даних NASA...</div>';

    const payload = {
        location: location,
        date: date
    };

    fetch(API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.error || `Помилка HTTP: ${response.status}`); });
        }
        return response.json();
    })
    .then(data => {
        const p = data.probabilities;
        
        // Зберігаємо повний об'єкт даних, щоб передати його функції завантаження
        const fullData = data;
        
        let html = `
            <div class="bg-white p-6 rounded-xl shadow-2xl mt-8">
                <div class="flex justify-between items-center mb-6">
                    <h2 class="text-2xl font-extrabold text-gray-800">Прогноз ризику для ${location}</h2>
                    <!-- КНОПКА ЗАВАНТАЖЕННЯ JSON -->
                    <button onclick='downloadJson(${JSON.stringify(fullData)}, "${location}", "${date}")'
                            class="px-4 py-2 bg-indigo-500 text-white text-sm font-bold rounded-lg 
                                   hover:bg-indigo-600 transition duration-150 shadow-md">
                        Завантажити JSON
                    </button>
                </div>
                
                <p class="text-sm text-indigo-500 mb-6">Запит: ${data.query}</p>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    
                    <!-- 1. Пляж -->
                    <div class="p-4 bg-blue-100 rounded-lg shadow-md border-b-4 border-blue-500 text-center">
                        <p class="text-lg font-semibold text-blue-800">Пляж (Bad: T &lt; 24°C або Rain &gt; 5мм)</p>
                        <p class="text-3xl font-bold mt-2 text-blue-700">${p.very_hot}</p>
                        <p class="text-sm text-gray-600">Ризик поганої погоди</p>
                    </div>

                    <!-- 2. Лижі -->
                    <div class="p-4 bg-gray-100 rounded-lg shadow-md border-b-4 border-gray-500 text-center">
                        <p class="text-lg font-semibold text-gray-800">Лижі (Bad: T &gt; 0°C)</p>
                        <p class="text-3xl font-bold mt-2 text-gray-700">${p.very_wet}</p>
                        <p class="text-sm text-gray-600">Ризик відсутності снігу</p>
                    </div>

                    <!-- 3. Туризм -->
                    <div class="p-4 bg-green-100 rounded-lg shadow-md border-b-4 border-green-500 text-center">
                        <p class="text-lg font-semibold text-green-800">Туризм (Bad: T &gt; 30°C або Rain &gt; 10мм)</p>
                        <p class="text-3xl font-bold mt-2 text-green-700">${p.hiking_prob}</p>
                        <p class="text-sm text-gray-600">Ризик некомфортності</p>
                    </div>

                    <!-- 4. Риболовля -->
                    <div class="p-4 bg-red-100 rounded-lg shadow-md border-b-4 border-red-500 text-center">
                        <p class="text-lg font-semibold text-red-800">Риболовля (Bad: Rain &gt; 10мм або Wind &gt; 10м/с)</p>
                        <p class="text-3xl font-bold mt-2 text-red-700">${p.fishing_prob}</p>
                        <p class="text-sm text-gray-600">Ризик сильного вітру/дощу</p>
                    </div>

                    <!-- 5. Фестиваль -->
                    <div class="p-4 bg-yellow-100 rounded-lg shadow-md border-b-4 border-yellow-500 text-center">
                        <p class="text-lg font-semibold text-yellow-800">Фестиваль (Bad: Rain &gt; 5мм або T &gt; 32°C)</p>
                        <p class="text-3xl font-bold mt-2 text-yellow-700">${p.very_uncomfortable}</p>
                        <p class="text-sm text-gray-600">Ризик екстремальних умов</p>
                    </div>
                </div>
            </div>
            ${createBarChart(p)} 
            ${createDataTable(data.raw_data_sample)}
        `;
        resultsDiv.innerHTML = html;
    })
    .catch(error => {
        resultsDiv.innerHTML = `<div class="text-red-600 font-bold p-4 bg-red-100 rounded-lg shadow-lg">
            <h3 class="text-lg font-extrabold mb-2">ПОМИЛКА ПІДКЛЮЧЕННЯ</h3>
            <p><strong>1. Переконайтеся, що ваш сервер Flask запущений командою <code>flask run</code>.</strong></p>
            <p><strong>2. Перевірте консоль (F12) на наявність помилок CORS або мережі.</strong></p>
            <p class="mt-2">Деталі помилки: ${error.message || error}</p>
        </div>`;
        console.error('Error:', error);
    });
}