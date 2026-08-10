async function getNotifcation() {
    const url = "http://127.0.0.1:5001/notifications";
    const container = document.querySelector('.notifcationsCointainer');
    const template = document.getElementById('noifcationTemplate');

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        container.innerHTML = ''; // clear old notifications before re-adding

        Object.values(data).forEach(notif => {
            const clone = template.content.cloneNode(true);

            clone.querySelector('.motionDetecedText').textContent = notif.type + " Detected";
            clone.querySelector('.subText').textContent = notif.location;
            clone.querySelector('.noifcationPicture').src = notif.img;

            container.appendChild(clone);
        });

    } catch (error) {
        console.error("Fetch error:", error);
    }
}

getNotifcation();