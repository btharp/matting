#include "kdtree.h"
#include <math.h>
#include <stdlib.h>

// Using int type for sizes instead of size_t due to 32/64-bit issues.
void knn(
    float *data_points,
    float *query_points,
    int *out_neighbor_indices,
    float *out_neighbor_distances,
    const int n_data_points,
    const int n_query_points,
    const int point_dimension,
    const int k
){
    size_t *indices = (size_t*)malloc(n_data_points*sizeof(*indices));
    
    for (int i = 0; i < n_data_points; i++){
        indices[i] = i;
    }
    
    struct kdtree *tree = kdtree_init(
        data_points,
        indices,
        n_data_points,
        point_dimension);

    // Working array size must be 1 greater then k
    struct kdtree_neighbor neighbors[k + 1];
    
    for (int i = 0; i < n_query_points; i++){
        float *query_point = query_points + i*point_dimension;

        size_t n_neighbors = 0;
        kdtree_find_knn(tree, query_point, neighbors, &n_neighbors, k);

        for (size_t j = 0; j < n_neighbors; j++){
            *out_neighbor_indices++ = neighbors[j].index;
            *out_neighbor_distances++ = sqrt(neighbors[j].distance);
        }
    }

    kdtree_free(tree);
    free(indices);
}
