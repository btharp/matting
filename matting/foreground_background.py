from .util import solve_cg, vec_vec_outer, pixel_coordinates, inv2
from .util import resize_nearest, sparse_conv_matrix
import numpy as np
import scipy.sparse

try:
    from .ichol import ichol, ichol_solve
except Exception as e:
    pass

def estimate_fb_cf(
    image,
    alpha,
    ichol_threshold=1e-4,
    regularization=1e-5,
    neighbors=[(-1, 0), (1, 0), (0, -1), (0, 1)],
    max_iter=1000,
    atol=0.0,
    rtol=1e-5,
    print_info=False,
):
    """
    Estimate foreground and background of an image using a closed form approach.

    Based on:
        Levin, Anat, Dani Lischinski, and Yair Weiss.
        "A closed-form solution to natural image matting."
        IEEE transactions on pattern analysis and machine intelligence
        30.2 (2008): 228-242.

    ichol_threshold: float64
        Incomplete Cholesky decomposition threshold.

    regularization: float64
        Smoothing factor for undefined foreground/background regions.

    print_info:
        Wheter to print debug information during iterations.

    Returns
    -------

    foreground: np.ndarray of dtype np.float64
        Foreground image.

    background: np.ndarray of dtype np.float64
        Background image.

    max_iter, atol, rtol: np.float64
        see documentation of util.solve_cg
    """

    h, w = image.shape[:2]
    n = w * h

    a = alpha.flatten()

    # Build sparse linear equation system
    U = scipy.sparse.bmat([[
        scipy.sparse.diags(a),
        scipy.sparse.diags(1 - a)]])

    # Directional derivative matrices
    Ds = [
        sparse_conv_matrix(w, h, [0, dx], [0, dy], [1.0, -1.0])
        for dx, dy in neighbors]

    S = sum(
        D.T.dot(scipy.sparse.diags(regularization + np.abs(D.dot(a)))).dot(D)
        for D in Ds)

    V = scipy.sparse.bmat([
        [S, None],
        [None, S]])

    A = (U.T.dot(U) + V).tocsc()

    if print_info:
        print("computing incomplete Cholesky decomposition")

    # Build incomplete Cholesky decomposition
    L_ichol = ichol(A, ichol_threshold)

    if print_info:
        print("incomplete Cholesky decomposition computed")

    # Use incomplete Cholesky decomposition as preconditioner
    def precondition(x):
        return ichol_solve(L_ichol, x)

    foreground = np.zeros((h, w, 3))
    background = np.zeros((h, w, 3))

    # For each color channel
    for channel in range(3):
        if print_info:
            print("solving channel %d" % (1 + channel))

        image_channel = image[:, :, channel].flatten()

        b = U.T.dot(image_channel)

        # Solve large sparse linear equation system
        fb = solve_cg(A, b, precondition=precondition, max_iter=max_iter, atol=atol, rtol=rtol, print_info=print_info)

        foreground[:, :, channel] = fb[:n].reshape(h, w)
        background[:, :, channel] = fb[n:].reshape(h, w)

    foreground = np.clip(foreground, 0, 1)
    background = np.clip(background, 0, 1)

    return foreground, background


def estimate_fb_ml(
    input_image,
    input_alpha,
    min_size=2,
    growth_factor=2,
    regularization=1e-5,
    n_iter_func=2,
    print_info=False,
):
    """
    Estimate foreground and background of an image using a multilevel
    approach.

    min_size: int > 0
        Minimum image size at which to start solving.

    growth_factor: float64 > 1.0
        Image size is increased by growth_factor each level.

    regularization: float64
        Smoothing factor for undefined foreground/background regions.

    n_iter_func: func(width: int, height: int) -> int
        How many iterations to perform at a given image size.

    print_info:
        Wheter to print debug information during iterations.

    Returns
    -------

    F: np.ndarray of dtype np.float64
        Foreground image.

    B: np.ndarray of dtype np.float64
        Background image.
    """
    
    if not callable(n_iter_func):
        value = n_iter_func
        n_iter_func = lambda w, h: value

    assert(min_size >= 1)
    assert(growth_factor > 1.0)
    h0, w0 = input_image.shape[:2]

    if print_info:
        print("Solving for foreground and background using multilevel method")

    # Find initial image size.
    if w0 < h0:
        w = min_size
        # ceil rounding one level faster sometimes
        h = int(np.ceil(min_size * h0 / w0))
    else:
        w = int(np.ceil(min_size * w0 / h0))
        h = min_size

    if print_info:
        print("Initial size: %d-by-%d" % (w, h))

    # Generate initial foreground and background from input image
    F = resize_nearest(input_image, w, h)
    B = F.copy()

    while True:
        if print_info:
            print("New level of size: %d-by-%d" % (w, h))

        # Resize image and alpha to size of current level
        image = resize_nearest(input_image, w, h)
        alpha = resize_nearest(input_alpha, w, h)

        # Iterate a few times
        n_iter = n_iter_func(w, h)
        for iteration in range(n_iter):
            if print_info:
                print("Iteration %d of %d" % (iteration + 1, n_iter))

            x, y = pixel_coordinates(w, h, flat=True)

            # Make alpha into a vector
            a = alpha.reshape(w * h)

            # Build system of linear equations
            U = np.stack([a, 1 - a], axis=1)
            A = vec_vec_outer(U, U)
            b = vec_vec_outer(U, image.reshape(w * h, 3))

            # For each neighbor
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                x2 = np.clip(x + dx, 0, w - 1)
                y2 = np.clip(y + dy, 0, h - 1)

                # Vectorized neighbor coordinates
                j = x2 + y2 * w

                # Gradient of alpha
                da = regularization + np.abs(a - a[j])

                # Update matrix of linear equation system
                A[:, 0, 0] += da
                A[:, 1, 1] += da

                # Update rhs of linear equation system
                b[:, 0, :] += da.reshape(w * h, 1) * F.reshape(w * h, 3)[j]
                b[:, 1, :] += da.reshape(w * h, 1) * B.reshape(w * h, 3)[j]

            # Solve linear equation system for foreground and background
            fb = np.clip(np.matmul(inv2(A), b), 0, 1)

            F = fb[:, 0, :].reshape(h, w, 3)
            B = fb[:, 1, :].reshape(h, w, 3)

        # If original image size is reached, return result
        if w >= w0 and h >= h0:
            return F, B

        # Grow image size to next level
        w = min(w0, int(np.ceil(w * growth_factor)))
        h = min(h0, int(np.ceil(h * growth_factor)))

        F = resize_nearest(F, w, h)
        B = resize_nearest(B, w, h)


def estimate_foreground_background(
    image,
    alpha,
    method="ml",
    **kwargs
):
    if method == "cf":
        return estimate_fb_cf(image, alpha, **kwargs)
    elif method == "ml":
        return estimate_fb_ml(image, alpha, **kwargs)
    else:
        raise Exception("Invalid method %s: expected either cf or ml" % method)
