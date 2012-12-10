class ControllerURLs():
    controller_base="/grading_controller/"
    log_in= controller_base + "login/"
    log_out=controller_base +"logout/"
    status = controller_base + "status/"
    submit = controller_base + "submit/"
    get_submission_ml = controller_base + "get_submission_ml/"
    get_submission_in = controller_base + "get_submission_instructor/"
    put_result = controller_base + "put_result/"
    get_pending_count = controller_base + "get_pending_count/"
    get_eta_for_submission= controller_base + "get_submission_eta/"

class PeerGradingURLs():
    peer_grading_base="/peer_grading/"
    get_next_submission=peer_grading_base + "get_next_submission/"
    save_grade = peer_grading_base + "save_grade/"
    is_student_calibrated = peer_grading_base + "is_student_calibrated/"
    show_calibration_essay = peer_grading_base + "show_calibration_essay/"
    save_calibration_essay = peer_grading_base + "save_calibration_essay/"
    peer_grading = peer_grading_base + "peer_grading/"

class MLGradingURLs():
    pass

class StaffGradingURLs():
    staff_grading_base="/staff_grading/"
    get_next_submission= staff_grading_base + "get_next_submission/"
    save_grade= staff_grading_base + "save_grade/"
    get_problem_list= staff_grading_base + "get_problem_list/"

class XqueueURLs():
    xqueue_url_base="/xqueue/"
    log_in = xqueue_url_base + "login/"
    put_result= xqueue_url_base + "put_result/"
    get_submission = xqueue_url_base + "get_submission/"
    get_queuelen = xqueue_url_base + "get_queuelen/"