const pathIcon = document.getElementById('togglePathDeviation')
const pathSwitch = document.getElementById('offpath')
let pathDeviationStatus = false;

pathSwitch.addEventListener('change', function() {
    pathDeviationStatus = this.checked;
    updatePathStatus();
});

function updatePathStatus()
{
    if (pathDeviationStatus == true) {
        pathIcon.src = 'pathalert.png';
    }else{
        pathIcon.src = 'onPath.png';
    }
}