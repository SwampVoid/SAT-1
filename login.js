var loginBtn = document.getElementById("loginBtn")
var emailInput = document.getElementById("emailInput")
var passWord = document.getElementById("passWordInput")
var warnText = document.getElementById("warnText")
var privacyBtn = document.getElementById("privacyBtn")

function checkDetails() {
    if (emailInput.value == "Admin" && passWord.value == "Admin") {
        window.location.href = "index.html"
    } else {
        console.log("Incorrect password or username")

        warnText.style.opacity = 1
    }
}

loginBtn.addEventListener("click", function() {
    checkDetails();
})

emailInput.addEventListener("keydown", function(event)  { 
    if (event.key == "Enter") {
        event.preventDefault();

        checkDetails();
    }
})

passWord.addEventListener("keydown", function(event)  { 
    if (event.key == "Enter") {
        event.preventDefault();

        checkDetails();
    }
})

privacyBtn.addEventListener("click", function() {
    window.location.href = "privacyPolicy.html"
})