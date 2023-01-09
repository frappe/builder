export { pan, zoom }

function pan(element) {
  if (element.parentElement) {
    element.parentElement.addEventListener('mousemove', function (e) {
      if (e.buttons === 1) {
        let x = (element.previousX || 0) + e.movementX;
        let y = (element.previousY || 0) + e.movementY;
        element.style.transform = `translate(${x}px, ${y}px)`
        element.previousX = x;
        element.previousY = y;
      }
    })
  }
}

function zoom(element) {
  element.addEventListener('wheel', function (e) {
    e.preventDefault();
    let scale = (element.previousScale || 1) + e.deltaY * -0.01;
    element.style.transform = `scale(${scale})`
    element.previousScale = scale;
  })
  // element.addEventListener('gestureend', function (e) {
  //   console.log('e', e);
  //   e.preventDefault();
  //   let scale = (element.previousScale || 1) + e.scale * -0.01;
  //   element.style.transform = `scale(${scale})`
  //   element.previousScale = scale;
  // })
}