import cv2
import numpy as np
from typing import List, Tuple, Optional


def find_trapezoid_corners(image_path: str,
                           min_area: int = 1000,
                           epsilon_factor: float = 0.02) -> Optional[np.ndarray]:
    """
    Find the four corners of a trapezoid in a JPEG image.

    Args:
        image_path: Path to the JPEG image
        min_area: Minimum area threshold for contour filtering
        epsilon_factor: Factor for contour approximation (lower = more precise)

    Returns:
        numpy array of 4 corner points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] or None
    """

    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by area (largest first)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Look for quadrilateral (4-sided polygon)
    for contour in contours:
        area = cv2.contourArea(contour)

        # Skip small contours
        if area < min_area:
            continue

        # Approximate the contour
        perimeter = cv2.arcLength(contour, True)
        epsilon = epsilon_factor * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if we found a quadrilateral
        if len(approx) == 4:
            # Reshape to get coordinate pairs
            corners = approx.reshape(-1, 2)
            return corners

    print("No trapezoid/quadrilateral found in the image")
    return None


def find_football_field_corners(image_path: str) -> Optional[np.ndarray]:
    """
    Specialized function to find football field corners using color and shape analysis.
    Better suited for complex outdoor scenes with perspective distortion.
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None

    height, width = image.shape[:2]

    # Convert to HSV for better green field detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Define range for green field (adjust these values based on your field)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])

    # Create mask for green areas
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # Clean up the mask with morphological operations
    kernel = np.ones((5, 5), np.uint8)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)

    # Apply Gaussian blur to the mask
    green_mask = cv2.GaussianBlur(green_mask, (5, 5), 0)

    # Find contours in the green mask
    contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("No green areas found")
        return None

    # Find the largest contour (likely the field)
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)

    # Ensure the contour is large enough (adjust threshold as needed)
    min_field_area = width * height * 0.1  # Field should be at least 10% of image
    if area < min_field_area:
        print(f"Largest green area too small: {area} < {min_field_area}")
        return None

    # Approximate the contour to a polygon
    perimeter = cv2.arcLength(largest_contour, True)
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)

    # If we don't get exactly 4 points, try different epsilon values
    if len(approx) != 4:
        for eps_factor in [0.01, 0.03, 0.04, 0.05]:
            epsilon = eps_factor * perimeter
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            if len(approx) == 4:
                break

    if len(approx) == 4:
        return approx.reshape(-1, 2)
    else:
        print(f"Could not approximate to quadrilateral. Got {len(approx)} points")
        return None


def find_field_with_edge_enhancement(image_path: str) -> Optional[np.ndarray]:
    """
    Alternative approach using edge enhancement and filtering specifically for sports fields.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)

    # Apply adaptive threshold to handle varying lighting
    adaptive_thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY, 11, 2)

    # Apply morphological operations to clean up
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

    # Find contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by area and aspect ratio
    candidates = []
    min_area = width * height * 0.05

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h

        # Football fields are typically wider than they are tall
        if 1.2 < aspect_ratio < 3.0:
            perimeter = cv2.arcLength(contour, True)
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) == 4:
                candidates.append((area, approx.reshape(-1, 2)))

    if candidates:
        # Return the largest valid candidate
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None


def visualize_corners(image_path: str, corners: np.ndarray, output_path: str = None):
    """
    Visualize the detected corners on the original image.

    Args:
        image_path: Path to the original image
        corners: Array of 4 corner points
        output_path: Optional path to save the result image
    """
    image = cv2.imread(image_path)

    # Draw circles at corner points
    for i, corner in enumerate(corners):
        x, y = corner
        cv2.circle(image, (int(x), int(y)), 8, (0, 255, 0), -1)
        cv2.putText(image, f'P{i + 1}', (int(x + 10), int(y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Draw lines connecting the corners
    points = corners.astype(np.int32)
    cv2.polylines(image, [points], True, (0, 0, 255), 3)

    # Display the result
    cv2.imshow('Trapezoid Corners', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Save if output path provided
    if output_path:
        cv2.imwrite(output_path, image)
        print(f"Result saved to {output_path}")


def order_corners(corners: np.ndarray) -> np.ndarray:
    """
    Order corners in a consistent way: top-left, top-right, bottom-right, bottom-left.

    Args:
        corners: Array of 4 corner points

    Returns:
        Ordered array of corners
    """
    # Calculate the sum and difference of coordinates
    sum_coords = corners.sum(axis=1)
    diff_coords = np.diff(corners, axis=1)

    # Top-left has smallest sum, bottom-right has largest sum
    top_left = corners[np.argmin(sum_coords)]
    bottom_right = corners[np.argmax(sum_coords)]

    # Top-right has smallest difference (x-y), bottom-left has largest difference
    top_right = corners[np.argmin(diff_coords)]
    bottom_left = corners[np.argmax(diff_coords)]

    return np.array([top_left, top_right, bottom_right, bottom_left])


# Example usage with multiple approaches
if __name__ == "__main__":
    # Replace with your image path
    image_path = "field2.jpg"

    print("Trying multiple detection approaches...\n")

    # Method 1: Color-based detection (best for football fields)
    print("1. Trying color-based field detection...")
    corners = find_football_field_corners(image_path)

    if corners is not None:
        print("✓ Found field corners using color detection!")
    else:
        print("✗ Color-based detection failed")

        # Method 2: Edge enhancement approach
        print("\n2. Trying edge enhancement method...")
        corners = find_field_with_edge_enhancement(image_path)

        if corners is not None:
            print("✓ Found field corners using edge enhancement!")
        else:
            print("✗ Edge enhancement failed")

            # Method 3: Original method (for high-contrast images)
            print("\n3. Trying original detection method...")
            corners = find_trapezoid_corners(image_path, min_area=5000, epsilon_factor=0.03)

    if corners is not None:
        print("\nFound field corners:")

        # Order the corners consistently
        ordered_corners = order_corners(corners)

        for i, (x, y) in enumerate(ordered_corners):
            labels = ['Top-Left', 'Top-Right', 'Bottom-Right', 'Bottom-Left']
            print(f"{labels[i]}: ({x:.1f}, {y:.1f})")

        # Visualize the result
        visualize_corners(image_path, corners, "field_result.jpg")
    else:
        print("\nNo field corners found with any method.")
        print("Suggestions:")
        print("- Ensure the field is clearly visible and well-lit")
        print("- Try adjusting the green color range in find_football_field_corners()")
        print("- The field should occupy a significant portion of the image")


def debug_field_detection(image_path: str):
    """
    Debug function to visualize the intermediate steps of field detection.
    """
    image = cv2.imread(image_path)
    if image is None:
        return

    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Create green mask
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # Clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    cleaned_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_OPEN, kernel)

    # Display intermediate results
    cv2.imshow('Original', cv2.resize(image, (800, 600)))
    cv2.imshow('Green Mask', cv2.resize(green_mask, (800, 600)))
    cv2.imshow('Cleaned Mask', cv2.resize(cleaned_mask, (800, 600)))
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# Alternative approach using morphological operations for better edge detection
def find_trapezoid_corners_morphology(image_path: str) -> Optional[np.ndarray]:
    """
    Alternative method using morphological operations for better edge detection.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply morphological operations
    kernel = np.ones((3, 3), np.uint8)
    morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    # Threshold
    _, thresh = cv2.threshold(morph, 127, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Process contours similar to the main function
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1000:
            continue

        perimeter = cv2.arcLength(contour, True)
        epsilon = 0.02 * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) == 4:
            return approx.reshape(-1, 2)

    return None