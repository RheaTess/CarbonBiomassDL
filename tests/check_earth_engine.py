
import ee

PROJECT_ID = "forestcarbondl"


def main():
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)

    message = ee.String("Earth Engine connection successful")
    print(message.getInfo())

    image_count = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate("2024-01-01", "2024-02-01")
        .limit(1)
        .size()
        .getInfo()
    )
    print("Sentinel-2 images found:", image_count)


if __name__ == "__main__":
    main()
