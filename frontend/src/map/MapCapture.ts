import L from 'leaflet';
import html2canvas from 'html2canvas';

interface CaptureRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export class MapCapture {
  private overlay: HTMLElement;
  private selection: HTMLElement;
  private dimensions: HTMLElement;
  private isDrawing: boolean = false;
  private isResizing: boolean = false;
  private startX: number = 0;
  private startY: number = 0;
  private currentRect: CaptureRect = { x: 0, y: 0, width: 0, height: 0 };
  private resizeHandle: string | null = null;
  private initialRect: CaptureRect = { x: 0, y: 0, width: 0, height: 0 };

  constructor(_map: L.Map) {
    // Map parameter kept for future use (e.g., extracting bounds, metadata)
    // Prefixed with _ to indicate intentional non-use
    this.overlay = document.getElementById('captureOverlay')!;
    this.selection = document.getElementById('captureSelection')!;
    this.dimensions = this.selection.querySelector('.capture-dimensions')!;

    this.setupEventListeners();
  }

  private setupEventListeners() {
    // Export button
    const exportBtn = document.getElementById('exportBtn');
    exportBtn?.addEventListener('click', () => this.startCapture());

    // Cancel button
    const cancelBtn = document.getElementById('cancelCapture');
    cancelBtn?.addEventListener('click', () => this.cancelCapture());

    // Confirm button
    const confirmBtn = document.getElementById('confirmCapture');
    confirmBtn?.addEventListener('click', () => this.captureAndDownload());

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.overlay.style.display === 'flex') {
        this.cancelCapture();
      }
    });

    // Drawing events
    this.overlay.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    document.addEventListener('mouseup', () => this.handleMouseUp());

    // Resize handles
    const handles = this.selection.querySelectorAll('.capture-handle');
    handles.forEach((handle) => {
      handle.addEventListener('mousedown', (e) => this.handleResizeStart(e as MouseEvent));
    });
  }

  public startCapture() {
    console.log('Starting capture mode');
    this.overlay.style.display = 'flex';
    this.selection.classList.remove('active');
    this.isDrawing = false;
    this.isResizing = false;
  }

  private cancelCapture() {
    console.log('Canceling capture');
    this.overlay.style.display = 'none';
    this.selection.classList.remove('active');
    this.isDrawing = false;
    this.isResizing = false;
  }

  private handleMouseDown(e: MouseEvent) {
    if (e.target !== this.overlay && e.target !== this.selection) {
      return;
    }

    const rect = this.overlay.getBoundingClientRect();
    this.startX = e.clientX - rect.left;
    this.startY = e.clientY - rect.top;
    this.isDrawing = true;

    this.currentRect = {
      x: this.startX,
      y: this.startY,
      width: 0,
      height: 0,
    };

    this.selection.classList.add('active');
    this.updateSelection();
  }

  private handleMouseMove(e: MouseEvent) {
    if (!this.isDrawing && !this.isResizing) {
      return;
    }

    const rect = this.overlay.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    if (this.isDrawing) {
      this.currentRect.width = currentX - this.startX;
      this.currentRect.height = currentY - this.startY;

      // Normalize rect if dragging in negative direction
      if (this.currentRect.width < 0) {
        this.currentRect.x = this.startX + this.currentRect.width;
        this.currentRect.width = Math.abs(this.currentRect.width);
      } else {
        this.currentRect.x = this.startX;
      }

      if (this.currentRect.height < 0) {
        this.currentRect.y = this.startY + this.currentRect.height;
        this.currentRect.height = Math.abs(this.currentRect.height);
      } else {
        this.currentRect.y = this.startY;
      }

      this.updateSelection();
    } else if (this.isResizing && this.resizeHandle) {
      this.handleResize(currentX, currentY);
      this.updateSelection();
    }
  }

  private handleMouseUp() {
    if (this.isDrawing) {
      // Minimum size check
      if (this.currentRect.width < 50 || this.currentRect.height < 50) {
        this.selection.classList.remove('active');
      }
    }
    this.isDrawing = false;
    this.isResizing = false;
    this.resizeHandle = null;
  }

  private handleResizeStart(e: MouseEvent) {
    e.stopPropagation();
    this.isResizing = true;

    const target = e.target as HTMLElement;
    if (target.classList.contains('capture-handle-nw')) this.resizeHandle = 'nw';
    else if (target.classList.contains('capture-handle-ne')) this.resizeHandle = 'ne';
    else if (target.classList.contains('capture-handle-sw')) this.resizeHandle = 'sw';
    else if (target.classList.contains('capture-handle-se')) this.resizeHandle = 'se';

    // Store initial rect for resize calculations
    this.initialRect = { ...this.currentRect };
    this.startX = e.clientX;
    this.startY = e.clientY;
  }

  private handleResize(currentX: number, currentY: number) {
    const deltaX = currentX - this.currentRect.x;
    const deltaY = currentY - this.currentRect.y;

    switch (this.resizeHandle) {
      case 'nw':
        this.currentRect.x = currentX;
        this.currentRect.y = currentY;
        this.currentRect.width = this.initialRect.width + (this.initialRect.x - currentX);
        this.currentRect.height = this.initialRect.height + (this.initialRect.y - currentY);
        break;
      case 'ne':
        this.currentRect.y = currentY;
        this.currentRect.width = deltaX;
        this.currentRect.height = this.initialRect.height + (this.initialRect.y - currentY);
        break;
      case 'sw':
        this.currentRect.x = currentX;
        this.currentRect.width = this.initialRect.width + (this.initialRect.x - currentX);
        this.currentRect.height = deltaY;
        break;
      case 'se':
        this.currentRect.width = deltaX;
        this.currentRect.height = deltaY;
        break;
    }

    // Prevent negative dimensions
    if (this.currentRect.width < 50) this.currentRect.width = 50;
    if (this.currentRect.height < 50) this.currentRect.height = 50;
  }

  private updateSelection() {
    this.selection.style.left = `${this.currentRect.x}px`;
    this.selection.style.top = `${this.currentRect.y}px`;
    this.selection.style.width = `${this.currentRect.width}px`;
    this.selection.style.height = `${this.currentRect.height}px`;

    // Update dimensions display
    const width = Math.round(this.currentRect.width);
    const height = Math.round(this.currentRect.height);
    this.dimensions.textContent = `${width} × ${height} px`;
  }

  private async captureAndDownload() {
    console.log('Capturing area:', this.currentRect);

    try {
      // Hide the overlay and UI elements temporarily
      this.overlay.style.display = 'none';
      const exportBtn = document.getElementById('exportBtn');
      if (exportBtn) exportBtn.style.display = 'none';

      // Get the map container
      const mapContainer = document.getElementById('map');
      if (!mapContainer) {
        throw new Error('Map container not found');
      }

      // Calculate device pixel ratio for high quality
      const scale = 2; // 2x resolution for high quality

      // Capture the entire map at high resolution
      const canvas = await html2canvas(mapContainer, {
        scale: scale,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#0a0a0a',
        logging: false,
        imageTimeout: 0,
      });

      // Create a new canvas with the selected area
      const cropCanvas = document.createElement('canvas');
      const ctx = cropCanvas.getContext('2d');

      if (!ctx) {
        throw new Error('Could not get canvas context');
      }

      // Calculate crop dimensions at the scaled resolution
      const cropX = this.currentRect.x * scale;
      const cropY = this.currentRect.y * scale;
      const cropWidth = this.currentRect.width * scale;
      const cropHeight = this.currentRect.height * scale;

      cropCanvas.width = cropWidth;
      cropCanvas.height = cropHeight;

      // Draw the cropped portion
      ctx.drawImage(
        canvas,
        cropX, cropY, cropWidth, cropHeight,
        0, 0, cropWidth, cropHeight
      );

      // Convert to blob and download
      cropCanvas.toBlob((blob) => {
        if (!blob) {
          throw new Error('Could not create image blob');
        }

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        link.download = `flashover-map-${timestamp}.png`;
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);

        console.log('✓ Map exported successfully');
        this.cancelCapture();
      }, 'image/png', 1.0);

    } catch (error) {
      console.error('Failed to capture map:', error);
      alert('Failed to export map. Please try again.');
    } finally {
      // Restore UI
      this.overlay.style.display = 'none';
      const exportBtn = document.getElementById('exportBtn');
      if (exportBtn) exportBtn.style.display = 'flex';
    }
  }
}
