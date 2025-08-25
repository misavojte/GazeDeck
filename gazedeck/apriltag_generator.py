"""AprilTag marker generation and export functionality"""

import io
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

try:
    from pupil_labs.real_time_screen_gaze import marker_generator
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

from .config import config


class AprilTagGenerator:
    """Handles AprilTag marker generation and export"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # High resolution settings for clear printing
        self.marker_size_pixels = 400  # Much larger base size
        self.scale_factor = 2  # Additional scaling
        self.dpi = 300  # High DPI for printing
        
        # PDF settings
        self.page_size = A4  # A4 page
        self.margin = 2 * cm  # 2cm margins
        self.marker_print_size = 4 * cm  # 4cm x 4cm markers on paper
    
    def generate_marker_image(self, marker_id: int, high_res: bool = True) -> Optional[bytes]:
        """Generate high-resolution AprilTag marker image as PNG bytes"""
        if not DEPENDENCIES_AVAILABLE:
            self.logger.error("Required dependencies not available")
            return None
            
        try:
            # Generate marker pixels using Pupil Labs
            marker_pixels = marker_generator.generate_marker(marker_id=marker_id)
            
            # Convert to PIL Image
            image = Image.fromarray(marker_pixels)
            
            if high_res:
                # Scale up significantly for high resolution printing
                final_size = self.marker_size_pixels * self.scale_factor
                new_size = (final_size, final_size)
                # Use NEAREST to keep sharp edges for QR-like codes
                image = image.resize(new_size, Image.NEAREST)
            
            # Convert to RGB if it's not already (some markers might be grayscale)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save as high-quality PNG
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG', optimize=False, dpi=(self.dpi, self.dpi))
            img_bytes.seek(0)
            
            self.logger.info(f"Generated high-res marker {marker_id}: {image.size} pixels")
            return img_bytes.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error generating marker {marker_id}: {e}")
            return None
    
    def create_marker_with_label(self, marker_id: int, position: str, description: str) -> Optional[Image.Image]:
        """Create a marker with label and instructions"""
        if not DEPENDENCIES_AVAILABLE:
            return None
            
        try:
            # Generate the marker
            marker_bytes = self.generate_marker_image(marker_id, high_res=True)
            if not marker_bytes:
                return None
            
            # Load the marker image
            marker_img = Image.open(io.BytesIO(marker_bytes))
            
            # Create a larger canvas with space for labels
            canvas_width = marker_img.width + 100
            canvas_height = marker_img.height + 150  # Extra space for text
            
            # Create white background
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            # Paste marker in center-top area
            marker_x = (canvas_width - marker_img.width) // 2
            marker_y = 50
            canvas.paste(marker_img, (marker_x, marker_y))
            
            # Add labels
            draw = ImageDraw.Draw(canvas)
            
            try:
                # Try to use a nice font, fallback to default if not available
                title_font = ImageFont.truetype("arial.ttf", 24)
                desc_font = ImageFont.truetype("arial.ttf", 16)
            except:
                # Fallback to default font
                title_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()
            
            # Title
            title = f"AprilTag {marker_id} - {position.title()}"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (canvas_width - title_width) // 2
            draw.text((title_x, 10), title, fill='black', font=title_font)
            
            # Description
            desc_y = marker_y + marker_img.height + 20
            desc_lines = [
                description,
                f"Cut along dotted lines",
                f"Place in {position} corner of screen"
            ]
            
            for i, line in enumerate(desc_lines):
                line_bbox = draw.textbbox((0, 0), line, font=desc_font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = (canvas_width - line_width) // 2
                draw.text((line_x, desc_y + i * 25), line, fill='black', font=desc_font)
            
            # Add cutting guides (dotted border)
            self._add_cutting_guides(draw, canvas_width, canvas_height)
            
            return canvas
            
        except Exception as e:
            self.logger.error(f"Error creating labeled marker {marker_id}: {e}")
            return None
    
    def _add_cutting_guides(self, draw: ImageDraw.Draw, width: int, height: int):
        """Add dotted cutting guides around the marker"""
        margin = 10
        dash_length = 5
        
        # Top and bottom lines
        for y in [margin, height - margin]:
            for x in range(margin, width - margin, dash_length * 2):
                draw.line([(x, y), (min(x + dash_length, width - margin), y)], 
                         fill='gray', width=1)
        
        # Left and right lines
        for x in [margin, width - margin]:
            for y in range(margin, height - margin, dash_length * 2):
                draw.line([(x, y), (x, min(y + dash_length, height - margin))], 
                         fill='gray', width=1)
    
    def create_pdf_sheet(self, marker_info_list: List[Dict[str, Any]], output_path: Path) -> bool:
        """Create a PDF with all markers arranged for easy cutting"""
        if not DEPENDENCIES_AVAILABLE:
            self.logger.error("PDF generation requires reportlab")
            return False
            
        try:
            # Create PDF canvas
            c = canvas.Canvas(str(output_path), pagesize=self.page_size)
            page_width, page_height = self.page_size
            
            # Calculate layout (2x2 grid)
            markers_per_row = 2
            markers_per_col = 2
            
            available_width = page_width - (2 * self.margin)
            available_height = page_height - (2 * self.margin)
            
            cell_width = available_width / markers_per_row
            cell_height = available_height / markers_per_col
            
            # Simple title
            c.setFont("Helvetica-Bold", 16)
            title_y = page_height - self.margin + 10
            c.drawCentredString(page_width / 2, title_y, "GazeDeck AprilTag Markers")
            
            # Generate and place markers in logical positions
            # Arrange markers to match their actual screen positions
            marker_positions = {
                0: (0, 0),  # top-left
                1: (1, 0),  # top-right
                2: (1, 1),  # bottom-right
                3: (0, 1)   # bottom-left
            }
            
            for marker_info in marker_info_list:
                marker_id = marker_info["id"]
                if marker_id not in marker_positions:
                    continue
                
                col, row = marker_positions[marker_id]
                
                # Calculate position
                x = self.margin + (col * cell_width)
                y = page_height - self.margin - ((row + 1) * cell_height)
                
                self._add_marker_to_pdf(c, marker_info, x, y, cell_width, cell_height)
            
            # No instructions - keep it simple
            
            c.save()
            self.logger.info(f"PDF created successfully: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating PDF: {e}")
            return False
    
    def _add_marker_to_pdf(self, c: canvas.Canvas, marker_info: Dict[str, Any], 
                          x: float, y: float, cell_width: float, cell_height: float):
        """Add a single marker to the PDF at specified position"""
        try:
            marker_id = marker_info["id"]
            position = marker_info["position"]
            description = marker_info["description"]
            
            # Generate marker image
            marker_bytes = self.generate_marker_image(marker_id, high_res=True)
            if not marker_bytes:
                return
            
            # Create ImageReader for reportlab
            from reportlab.lib.utils import ImageReader
            temp_img = ImageReader(io.BytesIO(marker_bytes))
            
            # Calculate marker placement in cell - larger marker, minimal text
            marker_size = min(cell_width, cell_height) * 0.8  # 80% of cell size for bigger markers
            marker_x = x + (cell_width - marker_size) / 2
            marker_y = y + (cell_height - marker_size) / 2
            
            # Draw marker image
            c.drawImage(temp_img, marker_x, marker_y, 
                       width=marker_size, height=marker_size)
            
            # Add minimal labels - position them outside the marker area
            c.setFont("Helvetica-Bold", 10)
            title = f"ID {marker_id}"
            title_x = x + cell_width / 2
            title_y = y + 15  # Bottom of cell
            c.drawCentredString(title_x, title_y, title)
            
            c.setFont("Helvetica", 8)
            pos_text = position.replace('-', ' ').title()
            c.drawCentredString(title_x, title_y - 12, pos_text)
            
        except Exception as e:
            self.logger.error(f"Error adding marker to PDF: {e}")
    

    
    def save_all_markers(self, output_dir: Path, create_pdf: bool = True) -> Dict[str, Any]:
        """Save all markers as individual PNGs and optionally create a PDF sheet"""
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get marker information
            from .pupil_integration import pupil_integration
            markers_info = pupil_integration.get_marker_info()
            
            saved_files = []
            
            # Save individual PNG files
            for marker_info in markers_info:
                marker_id = marker_info["id"]
                position = marker_info["position"]
                
                # Generate high-res marker
                marker_bytes = self.generate_marker_image(marker_id, high_res=True)
                if marker_bytes:
                    filename = f"apriltag_{marker_id}_{position}.png"
                    file_path = output_dir / filename
                    
                    with open(file_path, 'wb') as f:
                        f.write(marker_bytes)
                    
                    saved_files.append(str(file_path))
                    self.logger.info(f"Saved marker {marker_id} to {file_path}")
            
            # Create PDF sheet
            pdf_path = None
            if create_pdf:
                pdf_path = output_dir / "apriltag_markers_sheet.pdf"
                pdf_success = self.create_pdf_sheet(markers_info, pdf_path)
                if pdf_success:
                    saved_files.append(str(pdf_path))
            
            return {
                "success": True,
                "message": f"Saved {len(markers_info)} markers to {output_dir}",
                "files": saved_files,
                "pdf_created": pdf_path is not None
            }
            
        except Exception as e:
            self.logger.error(f"Error saving markers: {e}")
            return {
                "success": False,
                "message": f"Error saving markers: {str(e)}"
            }


# Global instance
apriltag_generator = AprilTagGenerator()
