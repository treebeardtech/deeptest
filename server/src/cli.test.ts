import { upload } from "./cli";

test('uploads report to server', () => {
    upload("unit.xml")
});