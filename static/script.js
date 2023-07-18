// Get video element
const video = document.getElementById('video');

// Check if the browser supports accessing the camera
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  // Request access to the camera
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(function(stream) {
      // Set the video source to the user's camera stream
      video.srcObject = stream;
    })
    .catch(function(error) {
      console.error('Error accessing the camera:', error);
    });
}

// Variable to store the interval ID
let captureInterval;

// Function to capture and send frames
function captureAndSendFrame() {
  // Create a canvas element to draw the video frame
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext('2d');

  // Draw the current video frame onto the canvas
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Convert the canvas content to a Blob (image file)
  canvas.toBlob(function(blob) {
    // Create a FormData object to send the image file to the Flask server
    const formData = new FormData();
    formData.append('video_frame', blob);

    // Send the image file to the Flask server only if the server is available
    if (typeof navigator.onLine !== 'undefined' && navigator.onLine) {
      $.ajax({
        type: 'POST',
        url: '/process_js_frames',  // Update the URL to match the Flask route
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
          // Handle the server's response here
          console.log(response);
        },
        error: function(error) {
          console.error('Error sending video frame:', error);
        }
      });
    }
  }, 'image/jpeg');
}

// Start capturing and sending frames at a regular interval (e.g., every 100 milliseconds)
captureInterval = setInterval(captureAndSendFrame, 100);

// Stop capturing and sending frames when the window is closed or the page is unloaded
window.addEventListener('beforeunload', function() {
  clearInterval(captureInterval);
});
