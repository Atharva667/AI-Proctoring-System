 function setTheme(theme){

document.documentElement.setAttribute("data-theme", theme);

localStorage.setItem("theme", theme);

}

function loadTheme(){

const savedTheme = localStorage.getItem("theme") || "light";

document.documentElement.setAttribute("data-theme", savedTheme);

const toggle = document.getElementById("themeToggle");

if(toggle){

toggle.checked = savedTheme === "dark";

toggle.addEventListener("change", function(){

if(this.checked){
setTheme("dark");
}else{
setTheme("light");
}

});

}

}

window.addEventListener("DOMContentLoaded", loadTheme);