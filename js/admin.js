const tbody = document.getElementById('tableBody');

async function loadHistory() {
  try {
    const res = await fetch('http://127.0.0.1:5002/history');
    const history = await res.json();

    tbody.innerHTML = '';

    history.forEach(item => {
      const statusHTML = item.detected 
        ? `<span style="color:#22c55e">Detected</span>` 
        : `<span style="color:#ef4444">Not Detected</span>`;

      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${item.timestamp}</td>
        <td>${statusHTML}</td>
        <td>${item.image_name}</td>
        <td>${item.confidence.toFixed(2)}</td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:red;">Cannot connect to backend. Run app.py</td></tr>`;
  }
}

loadHistory();