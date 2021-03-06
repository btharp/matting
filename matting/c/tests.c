#include "kdtree.c"
#include "knn.c"

#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <stdint.h>

#define SWAP(T, a, b) { T temp = (a); (a) = (b); (b) = temp; }

uint32_t state = 0x12345678;

uint32_t rand32(){
    uint32_t x = state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    state = x;
    return x;
}

void naive_knn(
    float *data_points,
    float *query_points,
    int *out_neighbor_indices,
    float *out_neighbor_distances,
    const int n_data_points,
    const int n_query_points,
    const int point_dimension,
    const int k
){
    for (int i = 0; i < n_query_points; i++){
        int indices[k + 1];
        float distances[k + 1];
        
        for (int c = 0; c < k; c++){
            indices[c] = -1;
            distances[c] = 1e10f;
        }
        
        float *p = query_points + i*point_dimension;
        
        for (int j = 0; j < n_data_points; j++){
            float *q = data_points + j*point_dimension;
            
            float dist = 0.0f;
            
            for (int c = 0; c < point_dimension; c++){
                float d = p[c] - q[c];
                dist += d*d;
            }
            
            indices[k] = j;
            distances[k] = dist;
            
            for (int c = k; c > 0; c--){
                if (distances[c - 1] <= distances[c]) break;
                
                SWAP(float, distances[c - 1], distances[c]);
                SWAP(int, indices[c - 1], indices[c]);
            }
        }
        
        for (int c = 0; c < k; c++){
            *out_neighbor_indices++ = indices[c];
            *out_neighbor_distances++ = distances[c];
        }
    } 
}

float randf(){
    return (rand32() - 1) / (float)0xffffffff;
}

void test_knn(
    int n_data_points,
    int n_query_points,
    int point_dimension,
    int k
){
    float *data_points = (float*)malloc(n_data_points*point_dimension*sizeof(*data_points));
    float *query_points = (float*)malloc(n_query_points*point_dimension*sizeof(*query_points));
    
    for (int i = 0; i < n_data_points*point_dimension; i++){
        data_points[i] = randf();
    }
    
    for (int i = 0; i < n_query_points; i++){
        if (i > 0 && rand32() % 100 == 0){
            // make duplicate point
            int j = rand32() % i;
            for (int p = 0; p < point_dimension; p++){
                query_points[i*point_dimension + p] = query_points[j*point_dimension + p];
            }
        }else{
            // make new point
            for (int p = 0; p < point_dimension; p++){
                query_points[i*point_dimension + p] = randf();
            }
        }
    }
    
    int *neighbor_indices1 = (int*)malloc(n_query_points*k*sizeof(*neighbor_indices1));
    int *neighbor_indices2 = (int*)malloc(n_query_points*k*sizeof(*neighbor_indices2));
    
    float *neighbor_distances1 = (float*)malloc(n_query_points*k*sizeof(*neighbor_distances1));
    float *neighbor_distances2 = (float*)malloc(n_query_points*k*sizeof(*neighbor_distances2));
    
    naive_knn(data_points, query_points, neighbor_indices1, neighbor_distances1, n_data_points, n_query_points, point_dimension, k);
          knn(data_points, query_points, neighbor_indices2, neighbor_distances2, n_data_points, n_query_points, point_dimension, k);
    
    for (int j = 0; j < n_query_points*k; j++){
        assert(neighbor_distances1[j] == neighbor_distances2[j]);
        assert(neighbor_indices1[j] == neighbor_indices2[j]);
    }
    
    free(neighbor_indices1);
    free(neighbor_indices2);
    free(neighbor_distances1);
    free(neighbor_distances2);
    
    free(data_points);
    free(query_points);
}

void knn_test(){
    for (int k = 0; k < 5; k++){
        for (int point_dimension = 1; point_dimension <= 5; point_dimension++){
            int n_data_points = k + rand32() % 100;
            int n_query_points = rand32() % 100;
        
            test_knn(n_data_points, n_query_points, point_dimension, k);
            test_knn(k, n_query_points, point_dimension, k);
            test_knn(n_data_points, 0, point_dimension, k);
            test_knn(k, 0, point_dimension, k);
        }
    }
}

int main(){
    knn_test();
    printf("knn_test passed\n");
    
    return 0;
}
