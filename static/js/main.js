function copyLink() {
  var copyText = document.getElementById("trip-link").innerText;
  navigator.clipboard.writeText(copyText);
  document.getElementById("copy-btn").innerText = "Copied!";
  setTimeout(function () {
    document.getElementById("copy-btn").innerText = "Copy";
  }, 2000);
}

function selectAll() {
  let option = document.getElementById("select");
  let participants = document.getElementsByName("split_among");

  for (let participant of participants) {
    participant.checked = option.checked;
  }
}

function updateSelectAll() {
  let participants = document.getElementsByName("split_among");
  let selectAllBox = document.getElementById("select");

  let allChecked = true;

  for (let participant of participants) {
    if (!participant.checked) {
      allChecked = false;
      break;
    }
  }

  selectAllBox.checked = allChecked;
}

let currentForm = null;
function toggleEdit(expenseId) {
  const form = document.getElementById(`edit-form-${expenseId}`);

  if (currentForm && currentForm != form) {
    currentForm.classList.add("hidden");
  }

  form.classList.toggle("hidden");

  if (form.classList.contains("hidden")) {
    currentForm = null;
  } else {
    currentForm = form;
  }
}

setTimeout(function() {
    document.querySelectorAll('.flash-message').forEach(function(msg) {
        msg.style.transition = 'opacity 0.5s ease';
        msg.style.opacity = '0';
        setTimeout(function() { msg.style.display = 'none'; }, 500);
    });
}, 3000);