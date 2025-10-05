// result.js

// 1. Витягуємо місце
const place = JSON.parse(localStorage.getItem("chosenPlace") || "{}");
document.getElementById("placeName").textContent = place.name || "—";
document.getElementById("flag").textContent = place.country ? "🌍" : "🏳️";

// Показати фото міста (якщо є)
if (place.name && place.name.toLowerCase().includes("kyiv")) {
  document.getElementById("placePhoto").src = "./images/kyiv.png";
}

// 2. Витягуємо дату
const date = JSON.parse(localStorage.getItem("chosenDate") || "{}");
document.getElementById("dateUS").textContent = date.displayUS || "—";

// 3. Для прикладу генеруємо випадкові дані
function randomValue(min, max) {
  return (Math.random() * (max - min) + min).toFixed(1);
}

document.getElementById("mTemp").textContent = randomValue(-10, 35) + "°C";
document.getElementById("mPrec").textContent = randomValue(0, 10) + " mm";
document.getElementById("mWind").textContent = randomValue(0, 15) + " m/s";
document.getElementById("mRH").textContent = randomValue(30, 100) + "%";

// 4. Тестовий вердикт
document.getElementById("riskValue").textContent = randomValue(0, 100) + "%";
document.getElementById("riskLabel").textContent = "Moderate";

// Good/Bad правила приклад
document.getElementById("actTitle").textContent = "Go to the Beach";
document.getElementById("goodRules").innerHTML = "<li>T ≥ 28°C and P < 0.5 mm</li>";
document.getElementById("badRules").innerHTML = "<li>T < 24°C or P > 5 mm</li>";
document.getElementById("tips").textContent = "Take sunglasses and water with you!";
