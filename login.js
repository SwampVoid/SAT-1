var loginBtn = document.getElementById("loginBtn")
var emailInput = document.getElementById("emailInput")
var passWord = document.getElementById("passWordInput")
var warnText = document.getElementById("warnText")

loginBtn.addEventListener("click", function() {

    if (emailInput.value == "Admin" && passWord.value == "Admin") {
        window.location.href = "index.html"
    } else {
        console.log("Incorrect password or username")

        warnText.style.opacity = 1
    }
})