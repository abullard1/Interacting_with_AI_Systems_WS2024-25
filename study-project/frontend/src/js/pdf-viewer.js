/**
 * PDF Viewer Component
 * Handles PDF document display and navigation
 */

// PDF viewer configuration
pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.6.347/pdf.worker.min.js";

// PDF viewer state
const url = "/pdfs/study-consent-form.pdf";
let pdfDoc = null,
  pageNum = 1,
  pageRendering = false,
  pageNumPending = null,
  scale = getResponsiveScale(), // Use responsive scale instead of fixed 1.5
  canvas = document.getElementById("pdf-viewer"),
  ctx = canvas.getContext("2d");

const devicePixelRatio = window.devicePixelRatio || 1;

function getResponsiveScale() {
  const viewportWidth = window.innerWidth;
  
  if (viewportWidth <= 480) {
    return 0.8;
  } else if (viewportWidth <= 768) {
    return 1.0;
  } else if (viewportWidth <= 1024) {
    return 1.2;
  } else {
    return 1.5;
  }
}

function handleResize() {
  const newScale = getResponsiveScale();
  
  if (newScale !== scale) {
    scale = newScale;
    queueRenderPage(pageNum);
  }
}

function renderPage(num) {
  pageRendering = true;
  
  const loadingIndicator = document.getElementById("pdf-loading");
  if (loadingIndicator) loadingIndicator.classList.remove("d-none");

  pdfDoc.getPage(num).then(function (page) {
    const viewport = page.getViewport({ scale: scale });
    
    canvas.height = viewport.height * devicePixelRatio;
    canvas.width = viewport.width * devicePixelRatio;
    
    canvas.style.height = viewport.height + "px";
    canvas.style.width = viewport.width + "px";
    
    ctx.scale(devicePixelRatio, devicePixelRatio);

    const renderContext = {
      canvasContext: ctx,
      viewport: viewport,
      enableWebGL: true,
      renderInteractiveForms: true,
    };

    const renderTask = page.render(renderContext);
    renderTask.promise.then(function () {
      pageRendering = false;
      
      if (loadingIndicator) loadingIndicator.classList.add("d-none");

      if (pageNumPending !== null) {
        renderPage(pageNumPending);
        pageNumPending = null;
      }
    });
  });

  document.getElementById("page-num").textContent = num + " von ";
  
  updateButtonStates();
}

function queueRenderPage(num) {
  if (pageRendering) {
    pageNumPending = num;
  } else {
    renderPage(num);
  }
}

function onPrevPage() {
  if (pageNum <= 1) return;
  pageNum--;
  queueRenderPage(pageNum);
}

function onNextPage() {
  if (pageNum >= pdfDoc.numPages) return;
  pageNum++;
  queueRenderPage(pageNum);
}

function updateButtonStates() {
  const prevButton = document.getElementById("prev-page");
  const nextButton = document.getElementById("next-page");
  
  if (prevButton) {
    prevButton.disabled = pageNum <= 1;
  }
  
  if (nextButton) {
    nextButton.disabled = pageNum >= pdfDoc.numPages;
  }
}

document.getElementById("prev-page").addEventListener("click", onPrevPage);
document.getElementById("next-page").addEventListener("click", onNextPage);

window.addEventListener("resize", handleResize);

// PDF download handler
document.getElementById("download-pdf").addEventListener("click", function () {
  const link = document.createElement("a");
  link.href = url;
  link.download = "einwilligungserklaerung.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

// Initialize PDF document and render first page
pdfjsLib
  .getDocument(url)
  .promise.then(function (pdfDoc_) {
    pdfDoc = pdfDoc_;
    document.getElementById("page-count").textContent = pdfDoc.numPages;
    renderPage(pageNum);
  })
  .catch(function (error) {
    console.error("[PDF Viewer] Error loading PDF:", error);
    const errorElement = document.getElementById("pdf-error");
    if (errorElement) {
      errorElement.classList.remove("d-none");
      errorElement.textContent = "Fehler beim Laden des PDF-Dokuments. Bitte versuchen Sie es später erneut.";
    }
  });
