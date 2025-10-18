// run_fisheye.js
const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')
const https = require('https')
const http = require('http')
const url = require('url')

//------------------------------------------------------------
// Config
//------------------------------------------------------------
const BUILD_DIR = path.resolve(__dirname, '../build')
const BINARY = 'fisheyeStitcher'
const CURR_DIR = process.cwd()

const IMAGE_URL = 'https://photoplanet360.fr/wp-content/uploads/2022/02/P0130-sun.jpg'
const OUT_DIR = path.resolve(__dirname, '../stitched')
const IMG_NM = 'image'
const MLS_MAP_PATH = path.resolve(__dirname, '../utils/grid_xd_yd_3840x1920.yml.gz')
const ENB_LC = 'false'
const ENB_RA = 'false'

// Path where we'll download the image
const IMAGE_PATH = path.join(__dirname, 'temp_image.jpg')

//------------------------------------------------------------
// Helper: download image from URL
//------------------------------------------------------------
function downloadImage(fileUrl, outputPath) {
    return new Promise((resolve, reject) => {
        const parsedUrl = url.parse(fileUrl)
        const client = parsedUrl.protocol === 'https:' ? https : http

        client
            .get(fileUrl, (res) => {
                if (res.statusCode !== 200) {
                    reject(new Error(`Failed to get '${fileUrl}' (${res.statusCode})`))
                    return
                }

                const file = fs.createWriteStream(outputPath)
                res.pipe(file)

                file.on('finish', () => {
                    file.close(resolve)
                })
            })
            .on('error', (err) => {
                reject(err)
            })
    })
}

//------------------------------------------------------------
// Main
//------------------------------------------------------------
;(async () => {
    try {
        // Build step
        if (!fs.existsSync(BUILD_DIR)) {
            console.log('You need to build the code first')
            console.log('Help:')
            console.log('    mkdir build && cd build')
            console.log('    cmake ..')
            console.log('    make')
            process.exit(1)
        } else {
            process.chdir(BUILD_DIR)
            console.log(`Building ${BINARY}...`)
            execSync(`rm -f ./bin/${BINARY}`, { stdio: 'inherit' })
            execSync(`cmake ..`, { stdio: 'inherit' })
            execSync(`make -j 4`, { stdio: 'inherit' })
            process.chdir(CURR_DIR)
        }

        // Ensure output directory exists
        if (!fs.existsSync(OUT_DIR)) {
            fs.mkdirSync(OUT_DIR, { recursive: true })
        }

        // Download the image
        console.log(`Downloading image from ${IMAGE_URL}...`)
        await downloadImage(IMAGE_URL, IMAGE_PATH)
        console.log(`Image saved to ${IMAGE_PATH}`)

        // Run the fisheye stitcher
        console.log('\nRunning fisheye stitcher...\n')
        const cmd = `${BUILD_DIR}/bin/${BINARY} \
            --out_dir ${OUT_DIR} \
            --img_nm ${IMG_NM} \
            --img_path ${IMAGE_PATH} \
            --mls_map_path ${MLS_MAP_PATH} \
            --enb_light_compen ${ENB_LC} \
            --enb_refine_align ${ENB_RA} \
            --mode "image"`

        execSync(cmd, { stdio: 'inherit' })
        console.log('\nDone!')
    } catch (err) {
        console.error('Error:', err)
        process.exit(1)
    }
})()
