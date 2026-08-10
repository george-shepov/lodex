import c0 from './chunk00.js'
import c1 from './chunk01.js'
import c2 from './chunk02.js'
import c3 from './chunk03.js'
import c4 from './chunk04.js'
import c5 from './chunk05.js'

const encoded = [c0, c1, c2, c3, c4, c5].join('')
export const lodexVideoSrc = `data:video/mp4;base64,${encoded}`
