(function () {
  window.selectSlot = function (btn) {
    document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('slot-input').value = btn.dataset.value;
    document.getElementById('submit-btn').disabled = false;
  };
})();