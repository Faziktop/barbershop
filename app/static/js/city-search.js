(function () {
  const cityInput = document.getElementById('city-search');
  const cityDropdown = document.getElementById('city-dropdown');
  const cityIdInput = document.getElementById('city-id-input');
  const geoBtn = document.getElementById('geo-btn');
  const geoMsg = document.getElementById('geo-msg');

  if (!cityInput) return;

  const apiCitiesUrl = cityInput.dataset.citiesUrl;
  const apiFindCityUrl = cityInput.dataset.findCityUrl;
  let lastQuery = '';

  cityInput.addEventListener('input', function () {
    const q = this.value.trim();
    lastQuery = q;
    cityIdInput.value = '';
    if (q.length < 1) { cityDropdown.style.display = 'none'; return; }
    fetch(apiCitiesUrl + '?q=' + encodeURIComponent(q))
      .then(r => r.json())
      .then(list => {
        if (q !== lastQuery) return;
        cityDropdown.innerHTML = '';
        if (!list.length) {
          const d = document.createElement('div');
          d.className = 'list-group-item';
          d.style.background = '#111';
          d.style.color = '#888';
          d.textContent = 'Ничего не найдено';
          cityDropdown.appendChild(d);
          cityDropdown.style.display = 'block';
          return;
        }
        list.forEach(c => {
          const a = document.createElement('a');
          a.href = '#';
          a.className = 'list-group-item list-group-item-action';
          a.style.background = '#111';
          a.style.color = '#eee';
          a.textContent = c.name + (c.region ? ' — ' + c.region : '');
          a.onclick = (e) => {
            e.preventDefault();
            cityInput.value = c.name;
            cityIdInput.value = c.id;
            cityDropdown.style.display = 'none';
          };
          cityDropdown.appendChild(a);
        });
        cityDropdown.style.display = 'block';
      })
      .catch(() => { cityDropdown.style.display = 'none'; });
  });

  document.addEventListener('click', (e) => {
    if (!cityDropdown.contains(e.target) && e.target !== cityInput) {
      cityDropdown.style.display = 'none';
    }
  });

  if (geoBtn) {
    geoBtn.addEventListener('click', function () {
      geoMsg.textContent = 'Определяем...';
      if (!navigator.geolocation) {
        geoMsg.textContent = 'Геолокация недоступна.';
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          fetch(apiFindCityUrl + '?lat=' + pos.coords.latitude + '&lon=' + pos.coords.longitude)
            .then(r => r.json())
            .then(data => {
              if (data.ok) {
                const url = new URL(window.location.href);
                url.searchParams.set('city_id', data.city_id);
                window.location.href = url.toString();
              } else if (data.nearest) {
                geoMsg.textContent = `Ближайший — ${data.nearest} (${data.distance_km} км). Выберите вручную.`;
              } else {
                geoMsg.textContent = 'Не удалось определить. Выберите вручную.';
              }
            })
            .catch(() => { geoMsg.textContent = 'Ошибка запроса.'; });
        },
        () => { geoMsg.textContent = 'Доступ запрещён. Выберите город вручную.'; },
        { timeout: 8000 }
      );
    });
  }
})();