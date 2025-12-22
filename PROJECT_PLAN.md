# Candlr

This is a web-based application which allows people create 3d models for custom candle molds, based on pictures or a prompt.

## Appearance

The website should look and feel like a native application, not a website, but it should work on both mobile and desktop.

For the design direction, I want something sophisticated, not a corporate template. Avoid generic layouts, AI-looking gradients, or too much symmetry. The sites I admire have an organic, hand-crafted quality with unexpected details.

## Technologies

### Frontend

Use React for the frontend, unless there's a clearly better option.

### Backend

Use FastAPI if you need a backend.

## Features

This website helps users create silicone molds for pouring custom candles.

 * It starts with an image or a prompt provided by the user
   * In case of an image: extract a high-resolution portion of the image which should to made into a candle (automatic selection using Nano Banana Pro). Feel free to make small changes so it will work better as a candle.
     * Use Nano Banana Pro for this
   * In case of a prompt: rewrite the prompt to create an image to be turned into a candle and the use Nano Banana Pro to create the image
 * Create a depth map from the extracted image
   * Send a prompt from the backend to Nano Banana Pro to achieve this
 * The depth map is the basis for the candles, i.e., it represents the candle shape we want to pour.
   * Conceptually, we now need to 1) create a negative of the 3d model represented by this depth map, i.e., the silicone mold, and 2) a negative of the silicone mold for pouring the silicone mold.
   * Combine these two steps into a single step, i.e., create a 3d model which we can use to pour the silicone mold for the candle.
   * The user should be able to select:
     * Default wall thickness
     * Maximum mold dimensions
     * Whether to include registration marks or pouring channels in the mold design
 * Once the model is created, display it to the user and display a download button.
   * The download format is STL
 * Query LLM tools via the backend, i.e., API keys for Nano Banana Pro etc. are stored in the backend.
 * Users don't need to log in to use the tool
 * If you're not familiar with Nano Banana Pro, research it. It is a SOTA image generation AI tool.

## Testing

Write tests for the frontend and the backend.

## Logging

We do not collect any logs and we do not track anything.