---
layout: post
devto_id: 3432377
title: "Building a Vector Database That Never Decompresses Your Vectors"
date: 2026-03-30
description: "How I built tqdb, a pure-Go embeddable vector database that stores vectors in 4-bit quantized form and searches them without decompressing. Honest benchmarks across four datasets, from 91.9% recall on learned embeddings to 50.9% on SIFT, and what I learned about when quantization works and when it doesn't."
keywords: vector database, quantization, TurboQuant, Go, embeddings, approximate nearest neighbor, ANN, SIMD, IVF, Lloyd-Max, Hadamard
image: /assets/og-image.png
author: Scott Everitt
hero: /assets/hero-tqdb.png
cover: /assets/cover-tqdb.png
devto_id: 3432377
hashnode_id: 69cad9b853fa69c3991f9955
mentions:
  - name: tqdb
    repo: "https://github.com/scotteveritt/tqdb"
    lang: Go
    description: "Pure-Go embeddable vector database with 4-bit TurboQuant quantization, ScaNN-style IVF indexing, and memory-mapped search without decompression."
faq:
  - q: "What is tqdb?"
    a: "tqdb is a pure-Go, embeddable vector database that uses 4-bit quantization to compress vectors 8x and search them without decompression. It achieves 91.9% recall on learned embeddings like Gemini (d=3072) and opens in 10ms via memory-mapped I/O."
  - q: "How does tqdb compare to chromem-go?"
    a: "tqdb opens 620x faster (10ms vs 6.2s), searches 2.3-14x faster, uses 3.1x less disk (115 MB vs 362 MB), and stores everything in a single file instead of 25,411 files. The tradeoff is 91.9% recall instead of 100% exact search."
  - q: "What is TurboQuant?"
    a: "TurboQuant is a quantization algorithm from Google (ICLR 2026) that compresses vectors using random orthogonal rotation followed by Lloyd-Max scalar quantization. It requires no training data because the codebook is derived from the mathematical properties of unit vectors."
  - q: "Does 4-bit quantization work on all types of vectors?"
    a: "No. 4-bit TurboQuant works best on learned embeddings from models like Gemini and GloVe (80-92% recall). On SIFT descriptors it achieves only 50.9% recall at 4-bit, because SIFT vectors have a non-Gaussian distribution. Use 8-bit for non-embedding vector types."
---

![](/assets/hero-tqdb.png)

## Preamble: What vector search is all about

If you've spent any time near an LLM in the last couple of years, you've heard the term "embeddings." The idea is simple: take some text (or an image, or whatever), feed it through a neural network, and out comes a list of numbers, a vector. Texts that are semantically similar end up with vectors that point in roughly the same direction.

The immediate question is: given a query vector, how do you find the most similar ones in your database? You compute cosine similarity against every stored vector and take the top K. Simple enough.

```go
func CosineSimilarity(a, b []float64) float64 {
    var dot, normA, normB float64
    for i := range a {
        dot += a[i] * b[i]
        normA += a[i] * a[i]
        normB += b[i] * b[i]
    }
    return dot / (math.Sqrt(normA) * math.Sqrt(normB))
}
```

The problem is that these vectors are *big*. Modern embedding models like Gemini output 3,072-dimensional vectors. Each one is 3,072 float64s = 24,576 bytes. Store 25,000 of them and you're looking at 362 MB on disk, spread across 25,411 individual files if you're using a library like chromem-go.

How long does it take to load 25,411 files from disk and deserialize them? **6.2 seconds.** Every time your application starts.

I could talk a lot more about the history and theory of approximate nearest neighbor search, but I think we're straying too far from the article. The point is: I wanted something that could store vectors *compressed*, search them *without decompressing*, and open in *milliseconds* instead of seconds. That's what I ended up building.

---

## Compressing vectors without training data

### The naive approach: just use fewer bits

The obvious first idea is scalar quantization: clamp your float64 values to some range and discretize them into, say, 256 buckets (8-bit). Libraries like sqlite-vec do this. It works, but it's sloppy. You need to scan all your data to find the min/max range, outliers wreck your bucket distribution, and you're still using a full byte per coordinate.

Can we do better? Can we get down to 4 bits per coordinate, a 64x compression ratio from float64, while preserving the ability to actually find the right vectors?

It turns out Google published a paper at ICLR 2026 called [TurboQuant](https://arxiv.org/abs/2504.00456) that does exactly this. And the really beautiful part is that it needs **zero training data**. The codebook is derived purely from the mathematical properties of unit vectors.

### How TurboQuant works

<video autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1em 0;"><source src="/assets/animations/tqdb/quantize_pipeline.mp4" type="video/mp4"></video>

The pipeline is three steps. Here's the actual code:

```go
func (tq *TurboQuantMSE) Quantize(vec []float64) *tqdb.CompressedVector {
    // 1. Normalize: separate direction from magnitude
    norm := mathutil.NormalizeTo(unitBuf[:d], vec)

    // 2. Rotate: make coordinate distribution predictable
    tq.rotation.Rotate(rotated, unitBuf[:d])

    // 3. Per-coordinate Lloyd-Max quantization
    indices := make([]uint8, workDim)
    tq.codebook.QuantizeTo(indices, rotated)

    return &tqdb.CompressedVector{
        Norm:    float32(norm),
        Indices: indices,
    }
}
```

**Step 1: Normalize.** Split the vector into direction (unit vector on the sphere) and magnitude (a single float32). This separation is key. The direction is what carries semantic meaning, and we can compress it aggressively. The magnitude gets stored losslessly.

**Step 2: Rotate.** Apply a random orthogonal rotation. This is the insight from the paper that makes everything else work. After rotation by *any* orthogonal matrix, the coordinates of a random unit vector follow a known distribution that converges to Gaussian with standard deviation σ = 1/√d as the dimension grows. The distribution is *predictable without looking at the data*. This is what makes the quantizer data-oblivious.

**Step 3: Quantize.** Each rotated coordinate is independently assigned to its nearest centroid via binary search on precomputed boundaries. The result is one uint8 index per coordinate, using only 4 of 8 bits.

```go
func (c *Codebook) QuantizeTo(dst []uint8, values []float64) {
    bounds := c.Boundaries
    for i, v := range values {
        dst[i] = uint8(sort.SearchFloat64s(bounds, v))
    }
}
```

That's it. A binary search per coordinate. The boundaries were precomputed by a Lloyd-Max solver that runs once at initialization, takes about 10ms, and only depends on the dimension and bit-width, not on your actual data. You can quantize a vector the moment it arrives without ever having seen the rest of your corpus.

### The Lloyd-Max solver

<video autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1em 0;"><source src="/assets/animations/tqdb/lloyd_max.mp4" type="video/mp4"></video>

Okay, where do those magical boundaries come from? The Lloyd-Max algorithm finds the optimal scalar quantizer for a given probability distribution. We know the distribution is N(0, 1/√d) after rotation, so we can solve for the optimal centroids and boundaries analytically.

```go
func SolveCodebook(d, bits int, useExact bool) *Codebook {
    numLevels := 1 << bits
    sigma := 1.0 / math.Sqrt(float64(d))

    // Initialize centroids at Gaussian quantiles (faster convergence)
    norm := distuv.Normal{Mu: 0, Sigma: sigma}
    centroids := make([]float64, numLevels)
    for i := range numLevels {
        p := (2.0*float64(i) + 1.0) / (2.0 * float64(numLevels))
        centroids[i] = norm.Quantile(p)
    }

    // Lloyd-Max iteration
    for range 200 {
        // Boundaries = midpoints between adjacent centroids
        for i := range numLevels - 1 {
            boundaries[i] = (centroids[i] + centroids[i+1]) * 0.5
        }

        // Centroids = E[X | X in partition_i] via numerical integration
        for i := range numLevels {
            a, b := edges[i], edges[i+1]
            numerator := quad.Fixed(func(x float64) float64 {
                return x * pdf(x)
            }, a, b, 100, nil, 0)
            denominator := quad.Fixed(func(x float64) float64 {
                return pdf(x)
            }, a, b, 100, nil, 0)

            if denominator > 1e-15 {
                newCentroids[i] = numerator / denominator
            }
        }

        if maxShift < 1e-10 {
            break // converged
        }
    }
}
```

For 4-bit quantization, that's 16 centroids and 15 boundaries. The solver converges in well under 200 iterations. The codebook depends only on (dimension, bits) and the σ = 1/√d relationship, not on any actual data. This is what makes it so elegant: the same codebook works for *any* corpus of vectors with the same dimension.

---

## The rotation problem: 75 MB of matrix

So we have our quantizer. There's just one problem. The paper says to use a "random orthogonal rotation matrix." For d=3072, that's a 3072 × 3072 matrix of float64. That's **75 megabytes** just for the rotation. And applying it costs O(d²) per vector.

```
Rotation memory (d=3072):
  QR decomposition: 3072 × 3072 × 8 bytes = 75 MB
  Time per vector:  O(d²) = O(9.4 million) multiplications
```

This is... not great. Especially for an embeddable library where you want the whole thing to fit comfortably in a mobile app or CLI tool.

### Randomized Walsh-Hadamard Transform: 65 KB

<video autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1em 0;"><source src="/assets/animations/tqdb/hadamard_vs_qr.mp4" type="video/mp4"></video>

I found a 2024 paper called [QuaRot](https://arxiv.org/abs/2404.00456) that showed the Randomized Hadamard Transform works just as well (and in practice, *better*) than a full random orthogonal matrix. The formula is simple:

```
R = D₂ · H̃ · D₁
```

Where D₁ and D₂ are random ±1 diagonal matrices, and H̃ is the normalized Walsh-Hadamard Transform. Here's the implementation:

```go
type HadamardRotator struct {
    d      int       // original dimension
    padD   int       // padded to next power of 2
    signs1 []float64 // length padD, values ±1.0
    signs2 []float64 // length padD, values ±1.0
}

func (h *HadamardRotator) Rotate(dst, src []float64) {
    copy(dst[:d], src[:d])
    for i := d; i < padD; i++ {
        dst[i] = 0 // zero-pad to power of 2
    }

    // D₁: apply first random sign flip
    for i := range padD {
        dst[i] *= s1[i]
    }

    // H̃: normalized Walsh-Hadamard transform
    fwht(dst[:padD])

    // D₂: apply second random sign flip
    for i := range padD {
        dst[i] *= s2[i]
    }
}
```

The FWHT itself is the butterfly algorithm you might recognize from the FFT:

```go
func fwht(x []float64) {
    n := len(x)
    invSqrt2 := 1.0 / math.Sqrt(2.0)
    h := 1
    for h < n {
        for i := 0; i < n; i += h * 2 {
            for j := i; j < i+h; j++ {
                a, b := x[j], x[j+h]
                x[j] = (a + b) * invSqrt2
                x[j+h] = (a - b) * invSqrt2
            }
        }
        h *= 2
    }
}
```

The entire rotator stores two sign vectors of length 4096 (padded from 3072 to the next power of 2). That's 2 × 4096 × 8 = **65 KB**. Down from 75 MB. A **1,150x** reduction in memory.

And the time complexity drops from O(d²) to O(d log d). For d=3072, that's ~36,000 operations instead of ~9.4 million.

The best part? It actually produces *better* recall than the paper's approach. On our benchmark with 25K Gemini embeddings at d=3072:

| Config | Rotation | Bit allocation | Recall@10 | Memory |
|--------|----------|---------------|-----------|--------|
| Paper | QR | Prod (3+1) | ~85% | 75 MB |
| **tqdb** | **Hadamard** | **MSE-only (4+0)** | **91.9%** | **65 KB** |

I should be precise about what's happening here. We changed *two* things relative to the paper, not one: the rotation method AND the bit allocation strategy. The paper uses 3 bits for MSE quantization plus 1 bit for a QJL bias correction (the "Prod" variant). We use all 4 bits for MSE quantization with no bias correction.

To isolate the effects, I ran both configurations with Hadamard rotation:

| Config (both Hadamard) | Recall@10 |
|------------------------|-----------|
| MSE-only (4+0 bits) | **91.8%** |
| Prod (3+1 bits) | 89.2% |

So about 2.6 percentage points come from the bit allocation change, and the remaining ~4.3 points from switching QR to Hadamard. Both changes help, and they're additive. The Hadamard rotation provides more uniform energy spreading (all entries are ±1/√n), which means the Lloyd-Max codebook captures more of the signal in each coordinate. With that better rotation, the QJL bias correction becomes unnecessary, and the extra MSE bit matters more than the bias fix.

---

## Searching without decompression

Okay so we have efficiently compressed vectors. Now how do we search them?

### The decompression trap: 31ms

The obvious approach: for each query, decompress every stored vector and compute cosine similarity. The decompression is the reverse of compression: look up centroid values, un-rotate, rescale by the norm. The problem is that un-rotation is O(d log d) per vector, and you're doing it for all N vectors. For 25K vectors at d=3072, that's a lot of work.

### The asymmetric trick: also 31ms, but differently

<video autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1em 0;"><source src="/assets/animations/tqdb/asymmetric_search.mp4" type="video/mp4"></video>

Here's the insight that makes the whole system work, borrowed from Google's [ScaNN](https://github.com/google-research/google-research/tree/master/scann): you don't need to decompress the stored vectors. You can compute the score *in rotated space*.

The query gets rotated once (O(d log d)). Then for each stored vector, the score is just the inner product of the rotated query against the codebook centroids indexed by the stored indices. No decompression. No un-rotation. Just a lookup table.

```go
// The search inner loop (hot path)
indices := allIdx[i*d : i*d+d : i*d+d]

var dot0, dot1 float64
j := 0
for ; j <= d-8; j += 8 {
    dot0 += queryRotated[j]*centroids[indices[j]] +
        queryRotated[j+1]*centroids[indices[j+1]] +
        queryRotated[j+2]*centroids[indices[j+2]] +
        queryRotated[j+3]*centroids[indices[j+3]]
    dot1 += queryRotated[j+4]*centroids[indices[j+4]] +
        queryRotated[j+5]*centroids[indices[j+5]] +
        queryRotated[j+6]*centroids[indices[j+6]] +
        queryRotated[j+7]*centroids[indices[j+7]]
}
for ; j < d; j++ {
    dot0 += queryRotated[j] * centroids[indices[j]]
}
score := dot0 + dot1
```

Look at what's happening here. `indices` is a raw byte slice from the memory-mapped file, one byte per coordinate, each byte being a 4-bit index into the codebook. `centroids` is an array of 16 float64 values (for 4-bit quantization), 128 bytes total. **The entire centroid table fits in L1 cache and stays hot across all N vectors.**

The 8-way unrolled loop with two independent accumulators gives the CPU maximum instruction-level parallelism. `dot0` and `dot1` have no data dependency, so the FMA units stay busy. Each iteration loads 4 bytes from the stored vector, uses them as indices into the 16-entry centroid table, multiplies by the corresponding rotated query coordinates, and accumulates. No branches. No decompression. Just multiply-accumulate with a lookup table.

Since the vectors were unit-normalized before quantization, the inner product in rotated space equals cosine similarity. The math works out because orthogonal rotations preserve inner products.

The brute-force search over 25K vectors at d=3072 takes **31ms**, already 2.3x faster than chromem-go's exact search over uncompressed vectors.

---

## Making it faster: IVF partitioning

<video autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1em 0;"><source src="/assets/animations/tqdb/ivf_partitions.mp4" type="video/mp4"></video>

31ms is good. But we can do better by not looking at every vector.

The idea behind Inverted File (IVF) indexing is to cluster your vectors into partitions, and at query time only score vectors in the nearest partitions. It's the same idea as ScaNN.

```go
func buildIVF(allIndices []uint8, codebookCentroids []float64,
              workDim, n, numPartitions, nProbe int, deleted []bool) *ivfIndex {
    // Reconstruct rotated-space vectors from quantized indices
    vectors := make([][]float64, n)
    for i := range n {
        vec := make([]float64, workDim)
        off := i * workDim
        for j := range workDim {
            vec[j] = codebookCentroids[allIndices[off+j]]
        }
        vectors[i] = vec
    }

    // k-means++ initialization + Lloyd's algorithm
    centroids := kmeanspp(vectors, numPartitions, deleted)
    centroids = lloyds(vectors, centroids, numPartitions, workDim, deleted, 20)

    // Assign each vector to its nearest partition
    partitions := make([][]int, numPartitions)
    for i := range n {
        nearest := nearestCentroid(vectors[i], centroids)
        partitions[nearest] = append(partitions[nearest], i)
    }

    return &ivfIndex{centroids: centroids, partitions: partitions}
}
```

For 25K vectors, we use √25000 ≈ 158 partitions. At search time, we probe the nearest √158 ≈ 13 partitions. That means we score roughly 13/158 × 25,000 ≈ 2,055 vectors instead of 25,000.

The k-means itself operates in the same rotated/quantized space as the search. We reconstruct vectors by looking up centroid values from the quantized indices. No decompression needed, even for index building.

The result:

| Search Mode | Recall@10 | Latency | Speedup |
|-------------|-----------|---------|---------|
| Brute-force | 91.9% | 31ms | 1.0x |
| IVF default | 89.1% | 4.7ms | **6.6x** |
| IVF nProbe=2x | 90.7% | 8.5ms | 3.7x |

We lose ~3% recall for a 6.6x speedup. Not bad.

### Getting the recall back: rescoring

But what if you want that recall back? There's a simple trick: fetch more candidates than you need from the fast quantized path, then rescore the top ones with exact cosine similarity by dequantizing them.

```go
if opts.Rescore > 0 && len(topBuf) > 0 {
    recon := make([]float64, origDim) // single buffer reused for all candidates
    cv := tqdb.CompressedVector{Dim: origDim, Bits: bits}
    for k := range topBuf {
        cv.Norm = c.norms[topBuf[k].idx]
        cv.Indices = allIdx[topBuf[k].idx*d : topBuf[k].idx*d+d]
        c.quantizer.DequantizeTo(recon, &cv)
        topBuf[k].score = mathutil.CosineSimilarity(query, recon)
    }
    sort.Slice(topBuf, func(i, j int) bool {
        return topBuf[i].score > topBuf[j].score
    })
}
```

Note the single `recon` buffer reused across all candidates. The earlier version allocated a new `[]float64` per candidate, which added ~30KB of garbage per rescore query.

With rescore=30 on top of IVF:

| Config | Recall@10 | Latency | Speedup |
|--------|-----------|---------|---------|
| **IVF + rescore=30** | **91.9%** | **9.4ms** | **3.3x** |

Full recall recovered, still 3.3x faster than brute-force.

---

## The file format: one file to rule them all

Remember those 25,411 files? We replace them with one:

```
[Header: 64 bytes]
[Indices: N × workDim uint8]     ← hot path, mmap'd directly
[Norms: N × float32 LE]
[IDs: 2-byte-length-prefixed strings]
[Data: 4-byte-length-prefixed JSON blobs]
[Contents: 4-byte-length-prefixed strings]
```

The indices section, the part the search loop reads on every query, sits right at the front, immediately after the 64-byte header. When you open the file, the entire indices section is a zero-copy slice into the memory-mapped data. No deserialization. No copying. The OS pages it in as needed.

IDs, metadata, and content are loaded lazily via `sync.Once`, only when you actually ask for them.

Opening the file: **10ms.** Down from 6.2 seconds. That's a **620x** improvement.

---

## Why this ends up being faster than the alternatives

### No existing Go library does all four things

Here's the competitive landscape for pure-Go vector databases:

| Requirement | chromem-go | coder/hnsw | sqlite-vec | **tqdb** |
|-------------|-----------|-----------|-----------|---------|
| Pure Go (no CGO) | Yes | Yes | No (C) | **Yes** |
| Embeddable | Yes | Yes | Yes | **Yes** |
| ANN indexing | **No** | Yes | **No** | **Yes** |
| Built-in quantization | **No** | **No** | int8 only | **Yes** (4-bit) |

chromem-go stores uncompressed float32s in one-file-per-vector gob.gz format. It's pure Go and dead simple, but there's no ANN index, no quantization, and that 6.2-second startup. coder/hnsw has HNSW indexing but no quantization, so you're still storing and comparing full float64 vectors. sqlite-vec has basic int8 quantization but requires CGO.

tqdb occupies all four cells. That's not because I'm cleverer than the authors of those libraries. It's because quantization was the starting point, not an afterthought. When quantization is a first-class citizen, everything else (the file format, the search loop, the index building) falls into place around it.

### Cache pressure

The search inner loop reads one byte per coordinate from the stored vector and uses it as an index into a 16-entry centroid table. The centroid table (16 × 8 = 128 bytes) stays hot in L1 cache across all N vectors. The stored vectors themselves are 4,096 bytes each (4096 coordinates × 1 byte for d=3072), compared to 32,768 bytes for float64 storage. That's 8x more vectors per cache line.

When you're iterating over 25,000 vectors, fitting 8x more data in cache reduces pressure on L2/L3 significantly. This is one reason the quantized brute-force search (31ms) is 2.3x faster than chromem-go's exact search (72ms) despite doing the same O(N×d) work, because the working set simply fits better in cache.

### Data-oblivious quantization

Most quantization schemes (PQ, OPQ, ScaNN's learned quantization) require a training step over representative data. If your data distribution shifts, your codebook degrades. tqdb's codebook depends only on the mathematical properties of unit vectors in d dimensions, specifically the Gaussian distribution (σ = 1/√d) that falls out of the random rotation. No training, no distribution assumptions, no retraining when your data changes. You can quantize a vector the moment it arrives.

---

## Benchmarks: the good, the bad, and the dataset-dependent

### Standard ANN benchmarks: where things get honest

I started with our production dataset (25K Gemini embeddings, d=3072) where the numbers look great. But I wanted to know how the algorithm behaves on standard ANN benchmark datasets that other researchers use. So I built a reproducible benchmark harness, downloaded the canonical datasets from [ann-benchmarks](https://github.com/erikbern/ann-benchmarks), and ran them.

The results were humbling:

| Dataset | Type | d | N | 4-bit Recall@10 | 8-bit Recall@10 |
|---------|------|---|---|-----------------|-----------------|
| chromem-gemini | Learned embeddings | 3072 | 25K | **91.9%** | ~98% |
| glove-100 | Learned embeddings | 100 | 1.18M | **80.8%** | **96.6%** |
| sift-128 | SIFT descriptors | 128 | 1M | **50.9%** | **89.3%** |

At 4-bit, the algorithm works brilliantly on learned embeddings (Gemini, GloVe) and poorly on SIFT descriptors. This isn't a bug. The Lloyd-Max codebook is optimized for the Gaussian distribution N(0, 1/√d) that emerges from rotating *unit vectors*. Learned embeddings from models like Gemini and GloVe are approximately uniformly distributed on the unit sphere, which maps well to this assumption. SIFT descriptors are histograms of gradient orientations:they have a fundamentally different distribution that the Gaussian codebook can't capture well at low bit-widths.

At 8-bit the gap closes: 96.6% on GloVe, 89.3% on SIFT. More bits means more centroids (256 instead of 16), which can approximate any distribution well enough.

The honest takeaway: **4-bit TurboQuant works best on modern embedding models** (which is the actual use case for RAG and semantic search). If you're working with SIFT-like descriptors, use 8-bit or a different approach entirely.

I also learned that recall degrades at scale: SIFT at 10K vectors gives 75.7% recall, but at 1M vectors it drops to 50.9%. Larger datasets have denser near-neighbor neighborhoods, and quantization errors accumulate.

### Performance vs the wider ecosystem

Let me be upfront about where tqdb sits in the performance landscape. On standard benchmarks, C++ libraries with SIMD and HNSW graphs are *much* faster:

| System | Language | Recall@10 | QPS | Notes |
|--------|----------|-----------|-----|-------|
| hnswlib | C++ | 95% | 5,000-8,000 | HNSW graph, AVX2 |
| FAISS IVF+PQ | C++ | 95% | 1,800-3,600 | Quantized ANN |
| Weaviate | Go (server) | 92% | 450 | HNSW, includes HTTP overhead |
| **tqdb 8-bit brute** | **Pure Go** | **96.6%** | **20** | No CGO, embeddable |
| **tqdb 4-bit IVF** | **Pure Go** | **81.5%** | **40** | 8x memory compression |
| chromem-go | Pure Go | 100% | ~1 est. | Brute-force, no ANN |

We're 100-400x slower than hnswlib on raw QPS. That's the price of pure Go without SIMD intrinsics or hand-written assembly. Go's compiler does a respectable job auto-vectorizing our inner loops on ARM64 NEON, but it can't compete with hand-tuned AVX2 gather instructions.

The value proposition isn't raw speed. It's the combination of properties no other system offers: **pure Go + embeddable + quantized + ANN indexed**. If you need 10,000 QPS, use FAISS. If you need a single binary that cross-compiles to any platform, opens in 10ms, and fits 8x more vectors in memory, that's where tqdb lives.

### vs chromem-go (d=3072, our production workload)

| Metric | chromem-go | tqdb | Improvement |
|--------|-----------|------|-------------|
| Open time | 6.2s | **10ms** | **620x** |
| Search (brute-force) | 72ms | **31ms** | **2.3x** |
| Search (IVF indexed) | - | **5ms** | **14x** |
| Disk size | 362 MB | **115 MB** | **3.1x** |
| Files | 25,411 | **1** | |
| Recall@10 | 100% (exact) | **91.9%** | 4-bit quantization |

The 620x open time improvement is the headline number. Going from 6.2 seconds to 10 milliseconds means your application can start instantly instead of making the user stare at a loading screen. The disk size drops from 362 MB to 115 MB, still not tiny, but the entire index is a single memory-mapped file instead of 25,411 individual gob.gz files.

### Model compression: because why not

While I was at it, I also built a model weight compressor. Same algorithm, different use case. TinyLlama 1.1B in BF16 is 2.0 GB. In 4-bit TurboQuant, it's **581 MB**. Compression takes 3.1 seconds on 12 cores, parallelized across a channel-based fan-out pattern where each worker gets its own buffer to avoid allocation contention.

| | Original | Compressed |
|---|---|---|
| Size | 2.0 GB (BF16) | **581 MB** (4-bit) |
| Time | - | **3.1s** (12 cores) |
| Quality | - | **99.5%** cosine similarity |

---

## What I'd do differently

A few things I learned the hard way:

**Don't benchmark only your best-case dataset.** I originally wrote this post with only the Gemini d=3072 numbers, which made everything look fantastic. Running on SIFT-128 (50.9% recall at 4-bit) was a cold shower. The algorithm is genuinely excellent for modern learned embeddings, but the Gaussian assumption behind the codebook is not universal. If I'd only shipped the Gemini numbers, someone would have tried it on SIFT-like data and been rightfully upset.

**Separate your variables.** I initially attributed the full 7% recall improvement over the paper to the Hadamard rotation. It was actually ~4.3% from rotation and ~2.6% from using MSE-only instead of Prod bit allocation. Both changes matter, but conflating them is bad science.

**Know your competition.** tqdb does something no other pure-Go library does (quantized + ANN + embeddable). But the raw QPS numbers are 100-400x behind C++ HNSW implementations. That's not a failure, it's a design tradeoff. Pure Go means single-binary cross-compilation, no CGO, no C toolchain. But if someone needs 10,000 QPS at 95% recall, hnswlib or FAISS is the right answer, not tqdb.

**The QPS gap may narrow.** Go 1.26 shipped experimental SIMD intrinsics (`simd/archsimd`) that expose AVX2/AVX-512 directly from Go code, with no assembly files and no CGO. It's AMD64-only for now (ARM64 is planned), but once it stabilizes, the search inner loop could use hardware FMA and gather instructions that would close the gap to 4-10x instead of 100-400x. I'm watching this closely.

## Epilogue

The code is at [github.com/scotteveritt/tqdb](https://github.com/scotteveritt/tqdb), MIT licensed.

The whole thing started because I was annoyed at how long chromem-go took to open 25,000 files. One thing led to another and now there's an IVF index, a model compressor, a GGUF converter, and a quantized KV cache in there.

The part I'm most proud of is how little code it actually takes. The quantization pipeline is about 30 lines. The search inner loop is 10 lines. The Lloyd-Max solver is maybe 60 lines. When the math is clean, the code tends to be clean too.

The part I'm most *surprised* by is how dataset-dependent the results are. The same algorithm gives 91.9% recall on Gemini embeddings and 50.9% on SIFT descriptors. If there's one thing I want readers to take away, it's this: **always benchmark on your actual data, and always benchmark on data that makes you look bad too.**

If you have questions or feedback, feel free to open an issue. Thanks for reading.
